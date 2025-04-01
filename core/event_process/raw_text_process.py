# -*- coding: utf-8 -*-
import os
import sys
import re
import json
import asyncio
from typing import List, Dict, Optional, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.extract_bili_content import extract_content_from_bili
from utils.status_manager import StatusManager
from core.save_to_db.split_summary import process_summary
from utils.llm_api import LLMProcessor
from utils.get_emb import check_exists_event
from core.save_to_db.save_metadata import save_metadata_emb, save_relations


class EventProcessor:
    def __init__(self):
        self.processor = LLMProcessor()
        self.status_manager = StatusManager()

    def _update_status(self, user_id: Optional[str], status: str) -> None:
        """更新处理状态"""
        if user_id:
            print(f"Updating status for user {user_id}: {status}")
            self.status_manager.set_status(user_id, status)

    async def process_file(self, filename: str, text: str, user_db_path: Optional[str] = None, 
                           user_id: Optional[str] = None) -> None:
        """
        处理单个文件的主入口

        Args:       
            filename: 文件名
            text: 文本内容
            user_db_path: 用户数据库路径
            user_id: 用户ID

        """
        try:
            file_name = filename.split(".")[0]
            
            if user_id:
                print(f"开始处理文件: {file_name}, 用户ID: {user_id}")
                self._update_status(user_id, "正在处理内容")
            
            # 处理原始文本
            print(f"开始处理原始文本: {file_name}")
            await self._process_raw_text_workflow(file_name, text, user_db_path, user_id)
            
            if user_id:
                print(f"事件摘要生成完成: {file_name}")
                self._update_status(user_id, "完成")
            
        except Exception as e:
            print(f"处理文件 {filename} 时出错: {e}")
            import traceback
            print(traceback.format_exc())
            if user_id:
                self._update_status(user_id, "错误")
            raise e

    async def _process_raw_text_workflow(self, file_name: str, text: str, 
                                        user_db_path: str, user_id: Optional[str]) -> None:
        """
        处理原始文本的完整工作流

        Args:
            file_name: 文件名
            text: 文本内容
            user_db_path: 用户数据库路径
            user_id: 用户ID
        """
        # 1. 分析文本内容，提取事件
        timeline_events = await self._extract_timeline_events(text, user_id)
        
        # 2. 处理文本摘要
        await process_summary(text, file_name, user_db_path)
        
        # 3. 根据时间创建文件并处理事件
        await self._process_events_by_time(text, timeline_events, file_name, user_db_path, user_id)

    async def _extract_timeline_events(self, text: str, user_id: Optional[str]) -> List[Dict]:
        """
        从文本中提取事件

        Args:
            text: 文本内容
            user_id: 用户ID

        Returns:
            List[Dict]: 时间线事件列表
        """

        if user_id:
            self._update_status(user_id, "正在分析文本内容")
            
        timeline_response = self.processor.generate_response(
            "raw_text_process", 
            text, 
            output_format='json',
            model_type="dashscope"
        )
        
        res_events = json.loads(timeline_response)
        return res_events['events']

    async def _process_events_by_time(self, text: str, events: List[Dict], 
                                     file_name: str, user_db_path: str, 
                                     user_id: Optional[str]) -> None:
        """
        根据文本和事件列表处理事件

        Args:
            text: 文本内容
            events: 事件列表
            file_name: 文件名
            user_db_path: 用户数据库路径
            user_id: 用户ID
        """


        if user_id:
            self._update_status(user_id, "正在提取事件信息")
        
        # 1. 提取时间和事件标题
        time_list, event_titles = self._extract_time_and_titles(events)
        
        # 2. 检查事件是否存在并获取保存目录
        saving_dirs = await self._get_saving_directories(time_list, event_titles, user_db_path)
        
        # 3. 处理事件之间的关系
        await self._handle_event_relations(text, saving_dirs, file_name, user_db_path)
        
        # 4. 处理每个事件的摘要
        await self._process_individual_events(text, time_list, saving_dirs, file_name, user_db_path, user_id)

    def _extract_time_and_titles(self, events: List[Dict]) -> Tuple[List[str], List[str]]:
        """
        从事件列表中提取时间和标题

        Args:
            events: 事件列表

        Returns:
            Tuple[List[str], List[str]]: 时间和标题列表
        """
        time_list = [event['time'].split("年")[0] for event in events]
        event_titles = [event['event'] for event in events]
        return time_list, event_titles

    async def _get_saving_directories(self, time_list: List[str], event_titles: List[str], 
                                     user_db_path: str) -> List[str]:
        """
        获取事件名称，根据名称和时间检查是否已存在

        Args:
            time_list: 时间列表
            event_titles: 事件标题列表
            user_db_path: 用户数据库路径

        Returns:
            List[str]: 保存事件列表，包含已存在的事件或新事件
        """


        saving_events = []
        for time, title in zip(time_list, event_titles):
            exists_title = await self.check_event_exists(title, time, user_db_path)
            saving_event = exists_title if exists_title else title
            saving_events.append(saving_event)

        return saving_events
    


    async def _handle_event_relations(self, text: str, saving_dirs: List[str], 
                                     file_name: str, user_db_path: str) -> None:
        """
        处理并保存事件之间的关系

        Args:
            text: 文本内容
            saving_dirs: 保存事件列表
            file_name: 文件名
            user_db_path: 用户数据库路径
        """
        relations = await self.process_relations(text, saving_dirs, file_name)
        
        # 过滤存在的关系
        relations_to_save = [
            relation for relation in relations 
            if relation['event_1'] in saving_dirs and relation['event_2'] in saving_dirs
        ]
        
        if relations_to_save:
            await save_relations(relations_to_save, user_db_path)

    async def _process_individual_events(self, text: str, time_list: List[str], 
                                        saving_dirs: List[str], file_name: str, 
                                        user_db_path: str, user_id: Optional[str]) -> None:
        """
        处理每个单独的事件

        Args:
            text: 文本内容
            time_list: 时间列表
            saving_dirs: 保存事件列表
            file_name: 文件名
            user_db_path: 用户数据库路径
            user_id: 用户ID
        """
        for time, event in zip(time_list, saving_dirs):
            try:
                await self.process_event_summary(event, text, time, file_name, user_db_path, user_id)
            except Exception as e:
                print(f"处理事件 {event} 时出错: {e}")
                if user_id:
                    self._update_status(user_id, "错误")


    async def process_event_summary(self, event: str, text: str, time: str, 
                                   file_name: str, user_db_path: str, 
                                   user_id: Optional[str] = None) -> None:
        """
        处理单个事件的摘要并保存

        Args:
            event: 事件名称
            text: 文本内容
            time: 时间
            file_name: 文件名
            user_db_path: 用户数据库路径
            user_id: 用户ID
        """
        try:
            if user_id:
                self._update_status(user_id, "正在生成事件摘要")
                
            events_summary = self.processor.generate_response(
                "events_summary", 
                f"{event}\n\n文章内容：\n{text}", 
                output_format='json',
                model_type="dashscope",
                event_name=event
            )
           
            events_summary = json.loads(events_summary)
            events_summary['title'] = event
            await self.post_process_events(events_summary, time, file_name, user_db_path, user_id)
        except Exception as e:
            print(f"处理事件摘要时出错: {e}")
            if user_id:
                self._update_status(user_id, "错误")
            raise e

    async def check_event_exists(self, event: str, time_dir: str, user_db_path: str) -> Optional[str]:
        """
        检查事件是否存在

        Args:
            event: 事件名称
            time_dir: 时间目录
            user_db_path: 用户数据库路径
        """
        exists_event = await check_exists_event(event, time_dir, user_db_path)
        return exists_event if exists_event else None

    async def post_process_events(self, events_summary: Dict, time_dir: str, 
                                 file_name: str, user_db_path: str, 
                                 user_id: Optional[str] = None) -> None:
        """
        处理事件摘要并保存元数据

        Args:
            events_summary: 事件摘要
            time_dir: 时间目录
            file_name: 文件名
            user_db_path: 用户数据库路径
            user_id: 用户ID
        """
        try:
            # 提取事件摘要中的关键信息
            title = events_summary['title']
            time = events_summary['time']
            summary = events_summary['summary']
            people = events_summary['people']
            
            # 处理思想内容格式
            character_thought_pre = events_summary['thought']
            if isinstance(character_thought_pre, dict):
                character_thought = ''
                for key, value in character_thought_pre.items(): 
                    character_thought += f"{key}：{value}\n"
            else:
                character_thought = character_thought_pre
                
            author_view = events_summary['author']

            # 构建元数据
            metadata = {
                file_name: {
                    "figure": people,
                    "time": time,
                    "character_thought": character_thought,
                    "author_view": author_view,
                    "summary": summary,
                }
            }
           
            print(f'保存元数据: {metadata}')
            await save_metadata_emb(metadata=metadata, saving_dir=title, user_db_path=user_db_path)
            
        except Exception as e:
            print(f"处理事件摘要并保存元数据时出错: {e}")
            if user_id:
                self._update_status(user_id, "错误")
            raise e

    async def process_relations(self, text: str, events: List[str], file_name: str) -> List[Dict]:
        """
        处理事件之间的关系

        Args:
            text: 文本内容
            events: 事件列表
            file_name: 文件名

        Returns:
            List[Dict]: 事件关系列表
        """
        relations = self.processor.generate_response(
            "relations", 
            text, 
            output_format='json',
            model_type="kimi",
            EVENTS='"' + '\n"'.join(events) + '"',
            TEXT=text
        )

        res_relations = json.loads(relations)
        return res_relations['relations']

    


if __name__ == "__main__":
    pass
