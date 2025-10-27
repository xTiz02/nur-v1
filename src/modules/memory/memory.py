from typing import List

from vertexai.agent_engines import AgentEngine

from src.com.model.models import Fragment
from src.module import Module
from src.modules.llm.vertext_llm import VertexAgentEngine
from utils.constans import *
import requests
import json
import uuid
import asyncio
import copy

from src.com.repository.memory_repo import PgVectorRepository


class Memory(Module):

    def __init__(self, signals, agent: VertexAgentEngine, enabled=True):
        super().__init__(signals, enabled)

        self.API = self.API(self)
        self.prompt_injection.text = ""
        self.prompt_injection.priority = 60
        self.agent = agent
        self.processed_count = 0
        self.repo = PgVectorRepository(
            database="vector",
            user="user",
            password="pass",
            host="localhost",
            port="5432"
        )
        # self.chroma_client = chromadb.PersistentClient(path="./memories/chroma.db", settings=Settings(anonymized_telemetry=False))
        # self.collection = self.chroma_client.get_or_create_collection(name="neuro_collection")
        # print(f"MEMORY: Loaded {self.collection.count()} memories from database.")
        # if self.collection.count() == 0:
        #     print("MEMORY: No memories found in database. Importing from memoryinit.json")
        #     self.API.import_json(path="./memories/memoryinit.json")

    def get_prompt_injection(self):
        # Use recent messages and twitch messages to query the database for related memories
        query = ""

        for message in self.signals.recentTwitchMessages:
            query += message + "\n"

        for message in self.signals.history[-1]:
            if message["role"] == "user" and message["content"] != "":
                query += HOST_NAME + ": " + message["content"] + "\n"
            elif message["role"] == "assistant" and message["content"] != "":
                query += AI_NAME + ": " + message["content"] + "\n"

        memories = self.collection.query(query_texts=query, n_results=MEMORY_RECALL_COUNT)

        # Generate injection for LLM prompt

        self.prompt_injection.text = f"{AI_NAME} knows these things:\n"
        for i in range(len(memories["ids"][0])):
            self.prompt_injection.text += memories['documents'][0][i] + "\n"
        self.prompt_injection.text += "End of knowledge section\n"

        return self.prompt_injection

    async def run(self):
        # Periodically, check if at least 20 new messages have been sent, and if so, generate 3 question-answer pairs
        # to be stored into memory.
        # This is a technique called reflection. You essentially ask the AI what information is important in the recent
        # conversation, and it is converted into a memory so that it can be recalled later.
        while not self.signals.terminate:
            if self.processed_count > len(self.signals.history):
                print(f"Se reinició el conteo de mensajes procesados de memoria de {self.processed_count} a 0")
                self.processed_count = 0

            if len(self.signals.history) - self.processed_count >= 10:
                print("MEMORY: Generando nuevas memorias a partir del historial reciente de chat con la IA.")
                print(f"MEMORY: Procesados {self.processed_count} mensajes, total en historial {len(self.signals.history)}")

                chat_section = "Mensajes de usuarios: \n"
                for history in self.signals.history[-MEMORY_QUERY_MESSAGE_COUNT:]:
                    list_current: List[Fragment] = history["current"]
                    ai_response: str = history["ai_response"]

                    if len(list_current) > 0:
                        for fragment in list_current:
                            chat_section += fragment.display_name + ": " + fragment.message + "\n"
                    if ai_response != "":
                        chat_section += "AI response: " + "\n" + AI_NAME + ": " + ai_response + "\n"

                prompt = chat_section + MEMORY_PROMPT

                response = self.agent.memory(prompt)

                # Split each Q&A section and add the new memory to the database
                for memory in response.split("{qa}"):
                    memory = memory.strip()
                    if memory != "":
                        # Store in database vectors
                        self.repo.generate_embedding(memory)

                self.processed_count = len(self.signals.history)

            await asyncio.sleep(5)

    class API:
        def __init__(self, outer):
            self.outer = outer

        def create_memory(self, data):
            id = str(uuid.uuid4())
            self.outer.collection.upsert(id, documents=data, metadatas={"type": "short-term"})

        def delete_memory(self, id):
            self.outer.collection.delete(id)

        def wipe(self):
            self.outer.chroma_client.reset()
            self.outer.chroma_client.create_collection(name="neuro_collection")

        def clear_short_term(self):
            short_term_memories = self.outer.collection.get(where={"type": "short-term"})
            for id in short_term_memories["ids"]:
                self.outer.collection.delete(id)

        def import_json(self, path="./memories/memories.json"):
            with open(path, "r") as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    print("Error decoding JSON file")
                    return

            for memory in data["memories"]:
                self.outer.collection.upsert(memory["id"], documents=memory["document"], metadatas=memory["metadata"])

        def export_json(self, path="./memories/memories.json"):
            memories = self.outer.collection.get()

            data = {"memories": []}
            for i in range(len(memories["ids"])):
                data["memories"].append({"id": memories["ids"][i],
                                         "document": memories["documents"][i],
                                        "metadata": memories["metadatas"][i]})

            with open(path, "w") as file:
                json.dump(data, file)

        def get_memories(self, query=""):
            data = [];

            if query == "":
                memories = self.outer.collection.get()
                for i in range(len(memories["ids"])):
                    data.append({"id": memories["ids"][i],
                                 "document": memories["documents"][i],
                                 "metadata": memories["metadatas"][i]})
            else:
                memories = self.outer.collection.query(query_texts=query, n_results=30)
                for i in range(len(memories["ids"][0])):
                    data.append({"id": memories["ids"][0][i],
                                 "document": memories["documents"][0][i],
                                 "metadata": memories["metadatas"][0][i],
                                 "distance": memories["distances"][0][i]})

                # Sort memories by distance
                data = sorted(data, key=lambda x: x["distance"])
            return data