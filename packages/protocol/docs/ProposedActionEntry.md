# ProposedActionEntry

One built-but-unsent action inside a proposal. after: 'previous-confirmed' marks an action that must not be appended until the prior entry in the array has been confirmed by the node (e.g. automation_create's strategy_create -> automation_create race). A privileged executor must honor this ordering; a read-only proposer never appends anything itself, so it just carries the constraint as data.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**configuration** | [**UserActionConfiguration**](UserActionConfiguration.md) |  | 
**after** | **str** |  | [optional] 

## Example

```python
from octobot_protocol.models.proposed_action_entry import ProposedActionEntry

# TODO update the JSON string below
json = "{}"
# create an instance of ProposedActionEntry from a JSON string
proposed_action_entry_instance = ProposedActionEntry.from_json(json)
# print the JSON string representation of the object
print(ProposedActionEntry.to_json())

# convert the object into a dict
proposed_action_entry_dict = proposed_action_entry_instance.to_dict()
# create an instance of ProposedActionEntry from a dict
proposed_action_entry_from_dict = ProposedActionEntry.from_dict(proposed_action_entry_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


