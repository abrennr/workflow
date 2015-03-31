from workflow.core.models import Batch, Item_Current_Status
from django_filters import FilterSet

class BatchFilter(FilterSet):
    class Meta:
        model = Batch
        fields = ['collection', 'type', 'property_owner']

class ItemFilter(FilterSet):
    class Meta:
        model = Item_Current_Status
        fields = ['ready_action', 'has_problem']


