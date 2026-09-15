# ActionProposal

A batch of built-but-unsent user actions, transported out-of-band (QR code, deep link, file) between a read-only-connected client and a privileged one. v is the envelope version: a client MUST reject an unrecognised v with a distinguishable error rather than treat it as a malformed scan.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**v** | **int** |  | 
**kind** | **str** |  | 
**actions** | [**List[ProposedActionEntry]**](ProposedActionEntry.md) |  | 
**label** | **str** | Human-readable summary for a confirm screen, when the generic per-action name/action_type derivation isn&#39;t enough. | [optional] 
**created_at** | **datetime** |  | 

## Example

```python
from octobot_protocol.models.action_proposal import ActionProposal

# TODO update the JSON string below
json = "{}"
# create an instance of ActionProposal from a JSON string
action_proposal_instance = ActionProposal.from_json(json)
# print the JSON string representation of the object
print(ActionProposal.to_json())

# convert the object into a dict
action_proposal_dict = action_proposal_instance.to_dict()
# create an instance of ActionProposal from a dict
action_proposal_from_dict = ActionProposal.from_dict(action_proposal_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


