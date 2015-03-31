import workflow.core.models

def _handle_sequence_actions(this_sequence, actions):
    for i in range(len(actions)):
        action = workflow.core.models.Action.objects.get(pk=actions[i])
        was = workflow.core.models.Workflow_Sequence_Actions(workflow_sequence=this_sequence, action=action, order=i)
        was.save()

def create_sequence_from_form(cleaned_data):
    """Process passed form data to create a Workflow_Sequence object and the Workflow_Sequence_Actions M-to-M objects"""
    this_name = cleaned_data['name']
    this_description = cleaned_data['description']
    actions = cleaned_data['actions'].split(',')
    if cleaned_data['this_id']:
        try:
            sequence = workflow.core.models.Workflow_Sequence.objects.get(pk=cleaned_data['this_id'])
            sequence.name = this_name
            sequence.description = this_description
            sequence.actions.clear()
            sequence.save()
            _handle_sequence_actions(sequence, actions)
        except:
            pass
    else:
        sequence = workflow.core.models.Workflow_Sequence(name=this_name, description=this_description)
        sequence.save()
        _handle_sequence_actions(sequence, actions)

