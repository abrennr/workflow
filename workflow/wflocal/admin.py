from workflow.wflocal.models import DRL_Collection 
from workflow.wflocal.models import Source_Collection 
from workflow.wflocal.models import Building_Action 
from workflow.wflocal.models import Collection_Building_Actions
from workflow.wflocal.models import Metadata_Maps 
from workflow.wflocal.models import Local_Item
from workflow.wflocal.models import Local_Batch
from workflow.wflocal.models import Fedora_Site 
from workflow.wflocal.models import Fedora_Collection 
from django.contrib import admin

class DRL_CollectionAdmin(admin.ModelAdmin):
	list_display = ('collection', 'sort_field', 'derivative_type', 'url')

class Fedora_CollectionAdmin(admin.ModelAdmin):
	list_display = ('name', 'pid')

admin.site.register(DRL_Collection)
admin.site.register(Source_Collection)
admin.site.register(Building_Action)
admin.site.register(Collection_Building_Actions)
admin.site.register(Metadata_Maps)
admin.site.register(Local_Item)
admin.site.register(Local_Batch)
admin.site.register(Fedora_Site)
admin.site.register(Fedora_Collection)
