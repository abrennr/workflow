from workflow.retrographer.models import Tag
from django.contrib import admin

class TagAdmin(admin.ModelAdmin):
    list_filter = ('photo_id',)
    search_fields = ('photo_id',)
    
admin.site.register(Tag, TagAdmin)
