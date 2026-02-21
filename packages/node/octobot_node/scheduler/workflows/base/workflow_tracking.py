import typing
import pydantic
import dataclasses
import logging
import dbos as dbos_lib

import octobot_commons.dataclasses


CURRENT_STEP_KEY = "current_step"


class ProgressStatus(pydantic.BaseModel):
    previous_step: str
    previous_step_details: typing.Optional[dict] = None
    next_step: typing.Optional[str] = None
    next_step_at: typing.Optional[float] = None
    remaining_steps: typing.Optional[int] = None


async def get_current_step(workflow_id: str) -> typing.Optional[ProgressStatus]:
    return await dbos_lib.DBOS.get_event_async(workflow_id, CURRENT_STEP_KEY)


@dataclasses.dataclass
class Tracker(octobot_commons.dataclasses.MinimizableDataclass):
    name: str

    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger(self.name)

    async def set_current_step(self, progress_status: ProgressStatus):
        await dbos_lib.DBOS.set_event_async(CURRENT_STEP_KEY, progress_status)
        self.logger.info(f"Current step updated: {progress_status.model_dump(exclude_defaults=True)}")