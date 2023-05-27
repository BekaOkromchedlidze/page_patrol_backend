from azure.data.tables import TableClient, TableServiceClient

from .auth_config import auth_config


class TableStorage:
    def __init__(self):
        self.connection_string = auth_config.COSMOSDB_CONNECTION_STRING
        self.table_service = TableServiceClient.from_connection_string(
            conn_str=self.connection_string
        )

        self.table_service.create_table_if_not_exists("PagePatrol")
        self.table_service.create_table_if_not_exists("PatrolHistory")

        self.page_patrol_table_client = self.table_service.get_table_client(
            "PagePatrol"
        )
        self.patrol_history_table_client = self.table_service.get_table_client(
            "PatrolHistory"
        )

    def create_entity(self, table_client: TableClient, entity):
        table_client.create_entity(entity=entity)

    def query_entities(self, table_client: TableClient, query_filter):
        return table_client.query_entities(query_filter=query_filter)

    def get_entity(self, table_client: TableClient, partition_key, row_key):
        return table_client.get_entity(partition_key, row_key)

    def update_entity(self, table_client: TableClient, mode, entity):
        table_client.update_entity(mode=mode, entity=entity)

    def delete_entity(self, table_client: TableClient, partition_key, row_key):
        table_client.delete_entity(partition_key, row_key)
