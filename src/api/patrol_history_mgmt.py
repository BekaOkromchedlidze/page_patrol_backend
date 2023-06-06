import re
import uuid
from datetime import datetime
from operator import itemgetter
from typing import List

from fastapi import APIRouter, HTTPException
from requests_html import AsyncHTMLSession

from src.auth_config import auth_config
from src.logger_config import setup_logger
from src.models import PatrolHistory
from src.table_storage import TableStorage


class PatrolHistoryManagement:
    def __init__(self, table_storage: TableStorage):
        self.logger = setup_logger(__name__)
        self.router = APIRouter()
        self.table_storage = table_storage

        self.router.get("/page-patrol/{page_patrol_id}/history")(
            self.get_patrol_history
        )

    def record_scrape_history(
        self,
        partition_key: str,
        page_patrol_id: str,
        scrape_time: datetime,
        scrape_html_content: str,
    ):
        # Get user information from the authentication system
        patrol_history = PatrolHistory(
            PartitionKey=partition_key,
            RowKey=str(uuid.uuid4()),
            page_patrol_id=page_patrol_id,
            scrape_time=scrape_time,
            scrape_html_content=scrape_html_content,
        )

        self.logger.info(
            f"page_patrol_id: {page_patrol_id} - Recording new HTML content"
        )
        self.table_storage.create_entity(
            self.table_storage.patrol_history_table_client,
            entity=patrol_history.dict(),
        )

    def is_scrape_history_needed(
        self, page_patrol_id: str, scrape_html_content: str
    ) -> bool:
        history_entities = (
            self.table_storage.patrol_history_table_client.query_entities(
                query_filter=f"page_patrol_id eq '{page_patrol_id}'",
            )
        )
        history_entities = sorted(
            history_entities, key=itemgetter("scrape_time"), reverse=True
        )

        if len(history_entities) == 0:
            return True
        elif history_entities:  # Compare saved html with html scraped.
            previously_recorded_html = str(
                history_entities[0].get("scrape_html_content")
            )

            # Remove any reference of a token from htmls as these will generally always be different
            token_regex_pattern = 'token="+\\S+"'
            previously_recorded_html_without_token = re.sub(
                token_regex_pattern, "", previously_recorded_html
            )
            scraped_html_without_token = re.sub(
                token_regex_pattern, "", scrape_html_content
            )

            return previously_recorded_html_without_token != scraped_html_without_token
        else:
            return False

    # Retrieve all patrol history for page patrol entity
    async def get_patrol_history(self, page_patrol_id: str) -> List[PatrolHistory]:
        entities = self.table_storage.query_entities(
            self.table_storage.patrol_history_table_client,
            query_filter=f"page_patrol_id eq '{page_patrol_id}'",
        )

        # Sort entries based on scrape_time in descending order
        entities = sorted(entities, key=itemgetter("scrape_time"), reverse=True)

        # Convert entities to PatrolHistory instances
        patrol_histories = []
        for entity in entities:
            try:
                patrol_history = PatrolHistory(**entity)
                patrol_histories.append(patrol_history)
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        return patrol_histories

    async def send_push_notification(self, expo_push_token, title, message):
        headers = {
            "accept": "application/json",
            "accept-encoding": "gzip, deflate",
            "content-type": "application/json",
            "authorization": f"Bearer {auth_config.EXPO_TOKEN}",
        }

        data = {
            "to": expo_push_token,
            "title": title,
            "body": message,
        }

        asession = AsyncHTMLSession()
        try:
            resp = await asession.post(
                "https://exp.host/--/api/v2/push/send", headers=headers, json=data
            )  # type: ignore
            print(resp)
            return resp

        # except PushServerError as exc:
        #     # Log the error
        #     log.error(f"PushServerError: {exc}")
        # except (PushResponseError, ValidationError) as exc:
        #     # Handle malformed messages
        #     log.error(f"Malformed message: {exc}")
        except Exception as exc:
            # Handle any other exceptions
            self.logger.error(
                f"Unknown error occurred when sending push notification: {exc}"
            )
