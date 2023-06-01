import re
import uuid
from datetime import datetime
from operator import itemgetter

from fastapi import APIRouter

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

        if self.is_scrape_history_needed(page_patrol_id, scrape_html_content):
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

        if history_entities:  # Compare saved html with html scraped.
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
            self.logger.info(
                f"page_patrol_id: {page_patrol_id} - Scraped HTML is same as previously recorded"
            )
            return previously_recorded_html_without_token != scraped_html_without_token
        else:
            return False

    # Retrieve all patrol history for page patrol entity
    async def get_patrol_history(self, page_patrol_id: str):
        entities = self.table_storage.query_entities(
            self.table_storage.patrol_history_table_client,
            query_filter=f"page_patrol_id eq '{page_patrol_id}'",
        )
        # Sort entries based on scrape_time in descending order
        entities = sorted(entities, key=itemgetter("scrape_time"), reverse=True)

        return [dict(entity.items()) for entity in entities]
