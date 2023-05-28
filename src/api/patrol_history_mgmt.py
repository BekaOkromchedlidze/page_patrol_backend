import uuid
from datetime import datetime
from operator import itemgetter

from src.models import PatrolHistory
from src.table_storage import TableStorage


class PatrolHistoryManagement:
    def __init__(self, table_storage: TableStorage):
        self.table_storage = table_storage

    def record_scrape_history(
        self,
        page_patrol_id: str,
        scrape_time: datetime,
        scrape_html_content: str,
    ):
        patrol_history = PatrolHistory(
            PartitionKey=page_patrol_id,
            RowKey=str(uuid.uuid4()),
            page_patrol_id=page_patrol_id,
            scrape_time=scrape_time,
            scrape_html_content=scrape_html_content,
        )

        if self.is_scrape_history_needed(page_patrol_id, scrape_html_content):
            self.table_storage.create_entity(
                self.table_storage.patrol_history_table_client,
                entity=patrol_history.dict(),
            )

    def is_scrape_history_needed(
        self, page_patrol_id: str, scrape_html_content: str
    ) -> bool:
        history_entities = (
            self.table_storage.patrol_history_table_client.query_entities(
                query_filter=f"PartitionKey eq '{page_patrol_id}'",
            )
        )
        history_entities = sorted(
            history_entities, key=itemgetter("scrape_time"), reverse=True
        )

        if history_entities:
            return history_entities[0].get("scrape_html_content") != scrape_html_content
        else:
            return True