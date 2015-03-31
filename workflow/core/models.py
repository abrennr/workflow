from django.db import models
from django.contrib.auth.models import User
from django import forms
import csv
import StringIO
#import django_filters

MIME_TYPE_CHOICES = (
    ('IMAGE_TIFF', 'image/tiff'),
    ('IMAGE_JPEG', 'image/jpeg'),
    ('IMAGE_JP2', 'image/jp2'),
    ('IMAGE_PNG', 'image/png'),
    ('IMAGE_GIF', 'image/gif'),
    ('TEXT_CSV', 'text/csv'),
    ('TEXT_HTML', 'text/html'),
    ('TEXT_XML', 'text/xml'),
    ('APPLICATION_ZIP', 'application/zip'),
    ('APPLICATION_PDF', 'application/pdf'),

)

FILE_USE_CHOICES = (
    ('MASTER', 'master'),
    ('TARGET', 'target'),
    ('THUMB', 'thumbnail'),
    ('MARCXML', 'MARCXML'),
    ('FGDC', 'FGDC'),
    ('KML', 'KML'),
    ('VRA_CORE', 'VRA Core'),
    ('MODS', 'MODS'),
    ('DC', 'Dublin Core'),
    ('PDF', 'PDF'),
    ('METS', 'METS'),
    ('EAD', 'EAD'),
    ('COPYRIGHTMD', 'copyrightMD'),
    ('THUMB', 'thumbnail'),
    ('OCR_ZIP', 'ocr - zipped'),
    ('OTHER', 'other'),
)
    

class WorkflowBatchFileCsv(forms.FileField):
    def clean(self, data, initial=None):
        """
        Check that the file uploaded contains properly formatted data, 
        i.e. csv-formatted records with at least a digital object indentifier and a
        title field.  The identifier must not already exist in the system.
        """
        super(forms.FileField, self).clean(initial or data)
        if not self.required:
            return None
        elif not data and initial:
            return initial
    
        # UploadedFile objects should have name and size attributes.
        try:
            file_name = data.name
            file_size = data.size
        except AttributeError:
            raise ValidationError(self.error_messages['invalid'])

        if not file_name:
            raise ValidationError(self.error_messages['invalid'])
        if not file_size:
            raise ValidationError(self.error_messages['empty'])

        conflicting_ids = []
        duplicate_ids = []
        seen_ids = {}
        destination = open('/tmp/' + data.name, 'wb+')
        for chunk in data.chunks():
            destination.write(chunk)
        destination.close()
        csv_data = csv.DictReader(open('/tmp/' + data.name))
        for line in csv_data:
            try:
                item_do_id = line['id']
                item_title = line['name'] 
            except Exception as e:
                raise forms.ValidationError('The file does not seem to be in the expected csv format.' + str(e))
            try: 
                Item.objects.get(do_id=item_do_id)
                conflicting_ids.append(item_do_id)
            except Item.DoesNotExist:
                pass
            try: 
                seen_ids[item_do_id]
                duplicate_ids.append(item_do_id)
            except:
                seen_ids[item_do_id] = 1
        if len(conflicting_ids) > 0:
            raise forms.ValidationError('Items in the data file conflict with existing item identifiers: ' + ', '.join(conflicting_ids))    
        if len(duplicate_ids) > 0:
            raise forms.ValidationError('Items in the data file include duplicate item identifiers: ' + ', '.join(duplicate_ids))
        
        return data

class Collection(models.Model):
    c_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    def __unicode__(self):
        return self.c_id
    def get_ready_actions(self):
        """Gets list of actions for which items in this collection are ready.  Each actions has a numbered count attribute."""
        ready_actions = []
        distinct_actions = Item_Current_Status.objects.filter(item__collection_item__collection=self).values('ready_action').distinct()
        for a in distinct_actions:
            if not a['ready_action']:
                continue
            act = Action.objects.get(id=a['ready_action'])
            act.count = Item_Current_Status.objects.filter(item__collection_item__collection=self, ready_action=act).count()
            ready_actions.append(act)
        return ready_actions
    def get_item_actions(self):
        actions = []
        distinct_actions = Item_Actions_Status.objects.filter(item__collection_item__collection=self).values('action').distinct()
        for a in distinct_actions:
            if not a['action']:
                continue
            act = Action.objects.get(id=a['action'])
            act.count = Item_Actions_Status.objects.filter(item__collection_item__collection=self, action=act).count()
            act.count_complete = Item_Actions_Status.objects.filter(item__collection_item__collection=self, action=act, complete=True).count()
            act.count_ready = Item_Actions_Status.objects.filter(item__collection_item__collection=self, action=act, ready=True).count()
            actions.append(act)
        return actions
    def get_problem_item_count(self):
        """Gets count of items in this batch that have unresolved problems"""
        return Item_Current_Status.objects.filter(item__collection_item__collection=self, has_problem=True).count() 



# Actions that can be required by items
class Action(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField()
    def __unicode__(self):
        return self.name

class Item_Type(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField()
    def __unicode__(self):
        return self.name

class Property_Owner(models.Model):
    name = models.CharField(max_length=64)
    depositor = models.CharField(max_length=255)
    description = models.TextField()
    def __unicode__(self):
        return self.description

class Workflow_Sequence(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    actions = models.ManyToManyField(Action, through='Workflow_Sequence_Actions', blank=True, null=True)
    def __unicode__(self):
        return self.name
    def get_ordered_actions(self):
        return Workflow_Sequence_Actions.objects.filter(workflow_sequence=self).order_by('order')

class Workflow_Sequence_Actions(models.Model):
    workflow_sequence = models.ForeignKey(Workflow_Sequence)
    action = models.ForeignKey(Action)
    order = models.IntegerField()

# suggested id value is combination of collection id and date
class Batch(models.Model):
    name = models.CharField(max_length=64, unique=True)
    collection = models.ForeignKey(Collection)
    type = models.ForeignKey(Item_Type)
    property_owner = models.ForeignKey(Property_Owner, blank=True, null=True)
    description = models.TextField(blank=True)
    sequence = models.ForeignKey(Workflow_Sequence)
    item_count = models.IntegerField(blank=True, null=True, editable=False, default=0)
    date = models.DateField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return '%s [%s]' % (self.name, self.collection.c_id)

    def get_ready_actions(self):
        """Gets list of actions for which items in this batch are ready.  Each actions has a numbered count attribute."""
        ready_actions = []
        distinct_actions = Item_Current_Status.objects.filter(item__batch_item__batch=self).values('ready_action').distinct()
        for a in distinct_actions:
            if not a['ready_action']:
                continue
            act = Action.objects.get(id=a['ready_action'])
            act.count = Item_Current_Status.objects.filter(item__batch_item__batch=self, ready_action=act).count()
            ready_actions.append(act)
        return ready_actions
    def get_item_actions(self):
        actions = []
        distinct_actions = Item_Actions_Status.objects.filter(item__batch_item__batch=self).values('action').distinct()
        for a in distinct_actions:
            if not a['action']:
                continue
            act = Action.objects.get(id=a['action'])
            act.count = Item_Actions_Status.objects.filter(item__batch_item__batch=self, action=act).count()
            act.count_complete = Item_Actions_Status.objects.filter(item__batch_item__batch=self, action=act, complete=True).count()
            act.count_ready = Item_Actions_Status.objects.filter(item__batch_item__batch=self, action=act, ready=True).count()
            actions.append(act)
        return actions
    def get_problem_item_count(self):
        """Gets count of items in this batch that have unresolved problems"""
        return Item_Current_Status.objects.filter(item__batch_item__batch=self, has_problem=True).count() 


class Item(models.Model):
    do_id = models.CharField('identifier', max_length=64, unique=True)
    name = models.CharField(max_length=255)
    type = models.ForeignKey(Item_Type)
    property_owner = models.ForeignKey(Property_Owner, blank=True, null=True)
    primary_collection = models.ForeignKey(Collection)
    def __unicode__(self):
        return self.name

    def inherit_from_batch(self, batch, clobber=False):
        if clobber or not self.type_id:
            self.type = batch.type
        if clobber or not self.property_owner:
            self.property_owner = batch.property_owner
        if clobber or not self.primary_collection_id:
            self.primary_collection = batch.collection

    def ready_action(self):
        ics = Item_Current_Status.objects.get(item=self)
        return ics.ready_action

    def set_action_complete(self, action, complete='True'):
        ias = self.item_actions_status_set.get(action=action)
        if complete == 'True':
            if (not ias.ready):
                raise Exception('item %s is not ready to have action %s completed.' % (self.do_id, action.name,))
            ias.complete = True
            ias.ready = False
            ias.save()
        elif complete == 'False':
            if (not ias.complete):
                return
            ias.complete = False
            ias.ready = True
            ias.save()
            ics = Item_Current_Status.objects.get(item=self)
            ics.ready_action = ias.action
            ics.save()
            while (ias.get_next()):
                ias = ias.get_next()
                ias.complete = False
                ias.ready = False
                ias.save()

    def add_action(self, action, position):
        new_ias = Item_Actions_Status(item=self, action=action, order=position)
        position_exists = False
        try:
            ias = Item_Actions_Status.objects.get(item=self, order=(position))
            position_exists = True 
        except:
            pass
        if position_exists: 
            if (ias.ready or ias.complete):
                new_ias.ready = True
                ics = Item_Current_Status.objects.get(item=self)
                ics.ready_action = action
                ics.save()
            following_actions = []
            following_actions.append(ias)
            while ias.get_next():
                ias = ias.get_next()
                following_actions.append(ias)
            for f in following_actions:
                f.ready = False
                f.complete = False
                f.order = f.order + 1
                f.save()
        else:
            try:
                preceeding_ias = Item_Actions_Status.objects.get(item=self, order=(position-1))
                if (preceeding_ias.complete):
                    new_ias.ready = True
                    ics = Item_Current_Status.objects.get(item=self)
                    ics.ready_action = action
                    ics.save()
            except:
                pass

        new_ias.save()

    def remove_action(self, action):
        try:
            ias = Item_Actions_Status.objects.get(item=self, action=action)
            if ias.ready:
                self.set_next_action_ready(action)
            following_actions = []
            while ias.get_next():
                ias = ias.get_next()
                following_actions.append(ias)
            for f in following_actions:
                f.order = f.order - 1
                f.save()
            Item_Actions_Status.objects.get(item=self, action=action).delete()
        except:
            pass

    def set_action_ready(self, action, ready='True'):
        status = self.item_actions_status_set.get(action=action)
        if ready == 'True':
            status.ready = True
        else:
            status.ready = False
        status.save()

    def set_next_action_ready(self, action, ready='True'):
        ics = Item_Current_Status.objects.get(item=self)
        ias = self.item_actions_status_set.get(action=action)
        if (ias.get_next()):
            next_ias = ias.get_next()
            next_ias.ready = True
            next_ias.save()
            ics.ready_action = next_ias.action
        else:
            ics.ready_action = None
        ics.save()

    class Facet:
        fields = ['type', 'property_owner', 'primary_collection']
            
# Item_File associates a file with an item
class Item_File(models.Model):
    item = models.ForeignKey(Item)
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=255, blank=True, null=True)
    host = models.CharField(max_length=255, blank=True, null=True)
    size_bytes = models.IntegerField(blank=True, null=True, editable=False)
    mime_type = models.CharField(max_length=255, choices=MIME_TYPE_CHOICES, blank=True, null=True)
    use = models.CharField(max_length=255, choices=FILE_USE_CHOICES, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    def __unicode__(self):
        return self.name

# linking table for items belonging to collections
class Collection_Item(models.Model):
    item = models.ForeignKey(Item)
    collection = models.ForeignKey(Collection)

# linking table for items belonging to batches 
class Batch_Item(models.Model):
    item = models.ForeignKey(Item)
    batch = models.ForeignKey(Batch)


# linking table to hold item status
class Item_Actions_Status(models.Model):
    item = models.ForeignKey(Item)
    action = models.ForeignKey(Action)
    order = models.IntegerField()
    ready = models.BooleanField()
    complete = models.BooleanField()
    def get_next(self):
        try:
            next_order = self.order + 1
            return Item_Actions_Status.objects.get(order=next_order, item=self.item)
        except:
            return False

# transaction logs what users do to items 
class Transaction(models.Model):
    item = models.ForeignKey(Item)
    user = models.ForeignKey(User)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

class Problem(models.Model):
    item = models.ForeignKey(Item)
    user_reported = models.ForeignKey(User, related_name='user_reported')
    time_reported = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    resolved = models.BooleanField()
    user_resolved = models.ForeignKey(User, related_name='user_resolved', null=True, blank=True)
    time_resolved = models.DateTimeField(null=True, blank=True)
    notes_resolved = models.TextField(null=True, blank=True)

# this is a convenience table to join data for ease in accessing current status
class Item_Current_Status(models.Model):
    item = models.ForeignKey(Item)
    last_transaction = models.ForeignKey(Transaction, null=True)
    ready_action = models.ForeignKey(Action, null=True)
    has_problem = models.BooleanField(default=False)

class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ['type', 'collection', 'property_owner', 'name', 'description', 'sequence']
    collection = forms.ModelChoiceField(queryset=Collection.objects.all().order_by('c_id'))
    property_owner = forms.ModelChoiceField(queryset=Property_Owner.objects.all().order_by('name'))
    sequence = forms.ModelChoiceField(queryset=Workflow_Sequence.objects.all().order_by('name'))
    has_file = forms.BooleanField(initial=True,required=False)
    file = WorkflowBatchFileCsv(required=False)

class BatchFileForm(forms.Form):
    file = WorkflowBatchFileCsv(required=False)


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
    item_files = forms.CharField(required=False)


class SequenceForm(forms.ModelForm):
    class Meta:
        model = Workflow_Sequence 
        fields = ['name', 'description']
    actions = forms.CharField()
    actions.widget = forms.HiddenInput()
    this_id = forms.CharField(required=False)
    this_id.widget = forms.HiddenInput()

class ChangeStatusSetupForm(forms.ModelForm):
    class Meta:
        model = Item_Actions_Status
        fields = ['action', 'complete']

class ChangeStatusForm(forms.Form):
    item = forms.CharField()

class BatchChangeStatusForm(forms.Form):
    action = forms.CharField()
    complete = forms.CharField()    

class BatchChangeActiveForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ['active']

class ReportProblemForm(forms.Form):
    item = forms.CharField()
    description = forms.CharField(widget=forms.Textarea)

class ProblemForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = ['resolved', 'notes_resolved']

class ItemFileForm(forms.ModelForm):
    class Meta:
        model = Item_File

#class BatchFilter(django_filters.FilterSet):
#    class Meta:
#        model = Batch
#        fields = ['collection', 'type', 'property_owner']
#
#class ItemFilter(django_filters.FilterSet):
#    class Meta:
#        model = Item_Current_Status
#        fields = ['ready_action', 'has_problem']
