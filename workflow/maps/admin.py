from workflow.maps.models import Collection 
from workflow.maps.models import Volume 
from workflow.maps.models import Map_Sheet 
from workflow.maps.models import Georeferenced_Map_Sheet 
from workflow.maps.models import Reference_Layer
from django.contrib import admin

class MapSheetAdmin(admin.ModelAdmin):
    search_fields = ('do_id',)
    
admin.site.register(Collection)
admin.site.register(Volume)
admin.site.register(Map_Sheet, MapSheetAdmin)
admin.site.register(Georeferenced_Map_Sheet)
admin.site.register(Reference_Layer)
