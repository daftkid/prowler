from enum import Enum
from typing import Optional

from pydantic import BaseModel

from prowler.lib.logger import logger
from prowler.lib.scan_filters.scan_filters import is_resource_filtered
from prowler.providers.aws.lib.service.service import AWSService


class Kinesis(AWSService):
    def __init__(self, provider):
        # Call AWSService's __init__
        super().__init__(__class__.__name__, provider)
        self.streams = {}
        self.__threading_call__(self._list_streams)
        self.__threading_call__(self._list_tags_for_stream, self.streams.values())

    def _list_streams(self, regional_client):
        logger.info("Kinesis - Listing Kinesis Streams...")
        try:
            list_streams_paginator = regional_client.get_paginator("list_streams")
            for page in list_streams_paginator.paginate():
                for stream in page["StreamSummaries"]:
                    arn = stream["StreamARN"]
                    if not self.audit_resources or (
                        is_resource_filtered(arn, self.audit_resources)
                    ):
                        self.streams[arn] = Stream(
                            arn=arn,
                            name=stream["StreamName"],
                            region=regional_client.region,
                            status=StreamStatus(stream.get("StreamStatus", "ACTIVE")),
                        )
        except Exception as error:
            logger.error(
                f"{regional_client.region} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
            )

    def _list_tags_for_stream(self, stream):
        logger.info(f"Kinesis - Listing tags for Stream {stream.name}...")
        try:
            stream.tags = (
                self.regional_clients[stream.region]
                .list_tags_for_stream(StreamName=stream.name)
                .get("Tags", [])
            )
        except Exception as error:
            logger.error(
                f"{stream.region} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
            )


class StreamStatus(Enum):
    """Enum for Kinesis Stream Status"""

    ACTIVE = "ACTIVE"
    CREATING = "CREATING"
    DELETING = "DELETING"
    UPDATING = "UPDATING"


class Stream(BaseModel):
    """Model for Kinesis Stream"""

    arn: str
    region: str
    name: str
    status: StreamStatus
    tags: Optional[list]
