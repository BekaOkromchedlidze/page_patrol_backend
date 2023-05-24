from azure.data.tables import TableServiceClient

from .auth_config import auth_config

connection_string = auth_config.COSMOSDB_CONNECTION_STRING
table_service = TableServiceClient.from_connection_string(conn_str=connection_string)


table_service.create_table_if_not_exists("WebsiteMonitoring")
website_monitoring_table_client = table_service.get_table_client("WebsiteMonitoring")
