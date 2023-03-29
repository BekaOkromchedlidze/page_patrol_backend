from azure.data.tables import TableServiceClient

connection_string = "UseDevelopmentStorage=true"
table_service = TableServiceClient.from_connection_string(conn_str=connection_string)


table_service.create_table_if_not_exists("WebsiteMonitoring")
website_monitoring_table_client = table_service.get_table_client("WebsiteMonitoring")
