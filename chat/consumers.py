import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async

from .models import Thread, ChatMessage

class ChatConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        print("connected", event)
        
        other_user = self.scope['url_route']['kwargs']['username']
        me = self.scope['user']
        print(other_user, me)
        # print("=================scope=============\n", self.scope)
        thread_obj = await self.get_thread(me, other_user)
        self.thread_obj = thread_obj
        print("============thread_obj===========\n", thread_obj)
        chat_room = f"thread_{thread_obj.id}"
        self.chat_room = chat_room
        await self.channel_layer.group_add(
            chat_room,
            self.channel_name
        )

        await self.send({
            "type": "websocket.accept"
        })

    async def websocket_receive(self, event):
        print("receive", event)
        front_text = event.get('text', None)
        if  front_text is not None:
            dict_data = json.loads(front_text)
            msg = dict_data.get('message')
            print(msg)
            user = self.scope['user']
            username = user.username if user.is_authenticated else 'default'
            response_data = {
                'message': msg,
                'username': username,
            }
            await self.create_chat_message(msg)
            
            # broadcast the message event to be sent
            await self.channel_layer.group_send(
                self.chat_room,
                {
                    "type": "chat_message",
                    "text": json.dumps(response_data)
                },
            )

    async def chat_message(self, event):
        # send the actual message
        await self.send({
            "type": "websocket.send",
            "text": event['text'],
        })

            # await self.send({
            # "type": "websocket.send",
            # "text": json.dumps(response_data)
            # })
    async def websocket_disconnect(self, event):
        print("disconnected", event)

    @database_sync_to_async
    def get_thread(self, user, other_username):
        return Thread.objects.get_or_new(user, other_username)[0]

    @database_sync_to_async
    def create_chat_message(self, msg):
        return ChatMessage.objects.create(thread=self.thread_obj, user=self.scope['user'], message=msg)