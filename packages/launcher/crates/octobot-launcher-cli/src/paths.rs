pub const INSTANCES: &str = "/v1/instances";
pub const UPDATES_CHECK: &str = "/v1/updates/check";
pub const UPDATES_APPLY: &str = "/v1/updates/launcher";

pub fn instance(id: &str) -> String          { format!("{INSTANCES}/{id}") }
pub fn instance_start(id: &str) -> String    { format!("{INSTANCES}/{id}/start") }
pub fn instance_stop(id: &str) -> String     { format!("{INSTANCES}/{id}/stop") }
pub fn instance_restart(id: &str) -> String  { format!("{INSTANCES}/{id}/restart") }
pub fn instance_update(id: &str) -> String   { format!("{INSTANCES}/{id}/update") }
pub fn instance_status(id: &str) -> String   { format!("{INSTANCES}/{id}/status") }
