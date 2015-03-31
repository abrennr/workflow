from workflow.core.models import Action
from workflow.core.models import Item_Type 
from workflow.core.models import Property_Owner 
from workflow.core.models import Collection 
from workflow.core.models import Batch 
from workflow.core.models import Item
from workflow.core.models import Workflow_Sequence
from workflow.core.models import Workflow_Sequence_Actions
from django.contrib import admin

admin.site.register(Action)
admin.site.register(Item_Type)
admin.site.register(Property_Owner)
admin.site.register(Collection)
admin.site.register(Batch)
admin.site.register(Item)
admin.site.register(Workflow_Sequence)
admin.site.register(Workflow_Sequence_Actions)
