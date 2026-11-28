#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import fastapi
import pydantic

try:
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.enums as mobile_ui_enums
except ImportError:
    try:
        import mobile_ui.enums as mobile_ui_enums  # type: ignore[no-redef]
    except ImportError:
        import enums as mobile_ui_enums  # type: ignore[no-redef]

try:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import AdminUser, CurrentUser
    from tentacles.Services.Interfaces.node_api_interface.api.node_setup_gate import (
        ensure_node_unconfigured_for_first_run,
    )
except ImportError:
    from api.deps import AdminUser, CurrentUser  # type: ignore[no-redef]
    from api.node_setup_gate import ensure_node_unconfigured_for_first_run  # type: ignore[no-redef]

router = fastapi.APIRouter(tags=["mobile-ui"])


class MobileUiStatusResponse(pydantic.BaseModel):
    state: mobile_ui_enums.MobileUiState
    installed_version: str | None
    latest_version: str | None
    update_available: bool
    last_error: mobile_ui_enums.MobileUiErrorCode | None


@router.get("/status", response_model=MobileUiStatusResponse)
def get_mobile_ui_status(
    request: fastapi.Request,
    current_user: CurrentUser,
) -> MobileUiStatusResponse:
    store = request.app.state.mobile_ui_store
    return MobileUiStatusResponse(**store.get_status())


@router.post(
    "/install",
    response_model=MobileUiStatusResponse,
    status_code=fastapi.status.HTTP_202_ACCEPTED,
)
async def install_mobile_ui(
    request: fastapi.Request,
    admin_user: AdminUser,
) -> MobileUiStatusResponse:
    store = request.app.state.mobile_ui_store
    return MobileUiStatusResponse(**store.start_install())

@router.post("/check", response_model=MobileUiStatusResponse)
async def check_mobile_ui_update(
    request: fastapi.Request,
    admin_user: AdminUser,
) -> MobileUiStatusResponse:
    store = request.app.state.mobile_ui_store
    return MobileUiStatusResponse(**await store.check_for_update())


@router.get("/first-run/status", response_model=MobileUiStatusResponse)
def get_mobile_ui_first_run_status(request: fastapi.Request) -> MobileUiStatusResponse:
    ensure_node_unconfigured_for_first_run()
    store = request.app.state.mobile_ui_store
    return MobileUiStatusResponse(**store.get_status())


@router.post(
    "/first-run/install",
    response_model=MobileUiStatusResponse,
    status_code=fastapi.status.HTTP_202_ACCEPTED,
)
async def install_mobile_ui_first_run(
    request: fastapi.Request,
) -> MobileUiStatusResponse:
    ensure_node_unconfigured_for_first_run()
    store = request.app.state.mobile_ui_store
    return MobileUiStatusResponse(**store.start_install())

