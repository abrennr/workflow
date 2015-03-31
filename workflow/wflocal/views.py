from workflow.core.models import *
from workflow.wflocal.models import *
import workflow.core.views
import workflow.core.transaction as transaction
from workflow.core.createbatch import handle_item_extras, handle_files 
from workflow.wflocal.createbatch import handle_local_csv_items, handle_local_item_extras
from workflow.core.createsequence import create_sequence_from_form
from workflow.core.transaction import record_transaction
from workflow.core.status import set_status 
from workflow.core.filters import BatchFilter, ItemFilter 
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import get_object_or_404, render_to_response
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core import serializers
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import get_object_or_404, render_to_response
from django.db.models import Sum, Count
from django.forms.models import inlineformset_factory
from django.template import Context, loader, RequestContext
import datetime
import shutil
import sys
import json
import csv
import drlutils.django.utils
import drlutils.text.utils
import drlutils.collection_building.utils
import drlutils.repository.item


def collection_building(request):
    collections = workflow.core.views.sort_collections(Collection.objects.all())
    for c in collections:
        try:
            c.item_count = DRL_Collection.objects.get(collection=c).item_count 
            c.ready_items = DRL_Collection.objects.get(collection=c).completed_item_count 
        except:
            c.item_count = 'unknown'
            c.ready_items = 'unknown'
        try:
            c.actions = Collection_Building_Actions.objects.filter(collection=c).order_by('order')
        except:
            c.actions = None 
    t = loader.get_template('wflocal/collection_building.html')
    c = RequestContext(request, {
        'collections': collections,
    })
    return HttpResponse(t.render(c))

def collection_building_detail(request, collection_id):
    c = Collection.objects.get(c_id=collection_id)
    c.actions = Collection_Building_Actions.objects.filter(collection=c).order_by('order')
    if len(c.actions) == 0:
        actions_formset = inlineformset_factory(c, Collection_Actions, can_order=True, exclude=('order',))
        formset = actions_formset() 
        t = loader.get_template('wflocal/collection_building_form.html')
        c = RequestContext(request, { 'formset' : formset })
        return HttpResponse(t.render(c))
    
def refresh_metadata_files(request):
    if request.method == 'POST':
        item = Local_Item.objects.get(do_id=request.POST['id'])
        user = User.objects.get(pk=request.POST['user'])    
        drlutils.repository.item.ingest_object_metadata(item)
        record_transaction(None, item, user, 'refreshed item metadata files')
        return HttpResponseRedirect(reverse('workflow.wflocal.views.item_detail', args=[request.POST['id']]))
        

def item_to_problems(request):
    if request.method == 'POST':
        item = Item.objects.get(do_id=request.POST['id'])
        user = User.objects.get(pk=request.POST['user'])    
        repository_path = drlutils.django.utils.get_repository_path(item) 
        checkout_dir = '/usr/local/dlxs/prep/public/problems'
        jobFile = '/usr/local/dlxs/prep/public/w/workflow/jobs/{0}.job'.format(datetime.datetime.now().strftime("%y%m%d%f"))
        jobFile = open('/usr/local/dlxs/prep/public/w/workflow/jobs/job.job', 'w')
        jobFile.write('\n'.join(['move', repository_path, checkout_dir]))    
        jobFile.close()    
        files = Item_File.objects.filter(item=item)
        for file in files:
            if item.type.name == 'image' and file.use == 'MASTER':
                file.path = None
                file.size_bytes = None
                file.mime_type = None
                file.save()
            else:
                file.delete()
        record_transaction(None, item, user, 'exported files from repository to problems directory')
        return HttpResponseRedirect(reverse('workflow.wflocal.views.item_detail', args=[request.POST['id']]))

def stats(request):
    batches = Batch.objects.all()
    for b in batches:
        b_stats = Item_File.objects.filter(item__batch_item__batch=b, use='MASTER').aggregate(Sum('size_bytes'), Count('id')) 
        b.file_count = b_stats['id__count']
        b.file_size = drlutils.text.utils.get_humanized_bytes(b_stats['size_bytes__sum']) 
    t = loader.get_template('wflocal/stats.html')
    c = RequestContext(request, { 'batches': batches, })
    return HttpResponse(t.render(c))


def coll_rebuilds(request, coll_type='textclass'):
    colls = []
    if coll_type == 'textclass':
        colls = drlutils.collection_building.utils.get_textclass_colls_to_rebuild() 
    json_serializer = serializers.get_serializer("json")()
    response = HttpResponse()
    json_serializer.serialize(colls, ensure_ascii=False, stream=response)
    return response

def metadata_maps(request, this_schema='MODS'):
    if 'schema' in request.GET.keys():
        this_schema = request.GET['schema']
    colls = Metadata_Maps.objects.filter(schema=this_schema) 
    maps_dict = {}
    for c in colls:
        fields = c.mapping.split('\n')
        this_map_dict = {}
        for f in fields:
            [a,b] = f.split(':')
            this_map_dict[a] = b.strip()
        maps_dict[c.collection.c_id] = this_map_dict
    response = HttpResponse()
    json.dump(maps_dict, response)
    return response


def register_online_collection_items(request):
    if request.method == 'POST':
        coll_id = request.POST['coll_id']
        ids_string = request.POST['items']
        ids = split(ids_string, ',')
        for id in ids:
            c_i = Collection_Item.objects.get(item__do_id=id, collection__c_id=coll_id)
            status = Collection_Building_Item_Status.objects.get(item=c_i, action__name='release online')
            try:
                local_item = Local_Item.objects.get(do_id=id)
                assert local_item.pub_date
            except:
                item = Item.objects.get(do_id=id)
                local_item = Local_Item(item=item, online_pub_date=datetime.date.today())
                local_item.save()
            status.set_timestamp()
        return HttpResponse()
    else:
        return HttpResponse()

def get_online_items(request):
    after_date = request.GET.get('after_date', '1900-01-01')
    item_type = request.GET.get('item_type', 'text - cataloged')
    local_items = workflow.wflocal.models.Local_Item.objects.filter(online_pub_date__gt=after_date)
    rows = []
    for local_item in local_items:
        if local_item.type.name != item_type:
            continue
        this_url = drlutils.django.utils.get_url_for_item(local_item.do_id)
        this_name = drlutils.text.utils.filter_to_ascii(local_item.name)
        if item_type == 'text - cataloged':
            try:
                voyager_id = local_item.voyager_id
            except:
                voyager_id = ''
            rows.append([local_item.do_id, this_name, this_url, voyager_id])       
        else:   
            rows.append([local_item.do_id, this_name, this_url])
    response = HttpResponse('', mimetype='text/plain')
    c = csv.writer(response)
    c.writerows(rows)
    return response 
        
        

LIST_HEADERS = (
    ('Item ID', 'item__id'),
    ('name', 'item__name'),
    ('ready for', 'ready_action'),
    ('last action', 'last_transaction__description'),
    ('when', 'last_transaction__timestamp'),
    ('who', 'last_transaction__user__first_name'),
)


def sort_objects_by_name(objects):
    obj_dict = {}
    sorted_list = []
    for obj in objects:
        obj_dict[obj.name] = obj
    order = obj_dict.keys()
    order.sort()
    for o in order:
        sorted_list.append(obj_dict[o])
    return sorted_list

def sort_collections(objects):
    obj_dict = {}
    sorted_list = []
    for obj in objects:
        obj_dict[obj.c_id] = obj
    order = obj_dict.keys()
    order.sort()
    for o in order:
        sorted_list.append(obj_dict[o])
    return sorted_list

def sort_items(objects):
    obj_dict = {}
    sorted_list = []
    for obj in objects:
        obj_dict[obj.do_id] = obj
    order = obj_dict.keys()
    order.sort()
    for o in order:
        sorted_list.append(obj_dict[o])
    return sorted_list

def sort_objects_by_id(objects):
    obj_dict = {}
    sorted_list = []
    for obj in objects:
        obj_dict[obj.id] = obj
    order = obj_dict.keys()
    order.sort()
    for o in order:
        sorted_list.append(obj_dict[o])
    return sorted_list

def get_paged_items(items, request):
    paginator = Paginator(items, 25)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        return paginator.page(page)
    except (EmptyPage, InvalidPage):
        return paginator.page(paginator.num_pages)


def get_item(request):
    query = request.GET['q']
    if request.GET['lookup'] == 'identifier':
        matches =  Item.objects.filter(do_id__icontains=query).count()
    elif request.GET['lookup'] == 'name':
        matches =  Item.objects.filter(name__icontains=query).count()
    if matches == 1:
        if request.GET['lookup'] == 'name':
            item =  Item.objects.get(name__icontains=query)
        else:
            item = Item.objects.get(do_id__icontains=query)
        return HttpResponseRedirect(reverse('workflow.wflocal.views.item_detail', args=[item.do_id]))
    else:
        if request.GET['lookup'] == 'identifier':
            items =  Item.objects.filter(do_id__icontains=query)
        elif request.GET['lookup'] == 'name':
            items =  Item.objects.filter(name__icontains=query)
        t = loader.get_template('wflocal/item.html')
        c = RequestContext(request, {
            'items': items,
        })
        return HttpResponse(t.render(c))

def get_item_json(request, item_id):
    item = Local_Item.objects.get(do_id=item_id)
    object_dict = {}
    item_dict = {}
    file_dict = {}
    event_dict = {}
    batch_dict = {}
    problem_dict = {}
    fedora_site_dict = {}
    fedora_collection_dict = {}
    for field in Local_Item._meta.fields:
        name = field.name
        if name == 'item_ptr':
            continue
        try:
            val = str(getattr(item, name))
        except:
            val = getattr(item, name)
        item_dict[name] = val 
    item_dict['repository_path'] = drlutils.django.utils.get_repository_path(item)
    item_files = Item_File.objects.filter(item=item).order_by('name')
    for item_file in item_files:
        row = {}
        for field in Item_File._meta.fields:
            name = field.name
            val = str(getattr(item_file, name))
            row[name] = val 
        file_dict[item_file.name] = row
    #row = map((lambda f:getattr(object, f)), fieldnames)
    events = item.transaction_set.all()
    for event in events:
        row = {}
        for field in Transaction._meta.fields:
            name = field.name
            val = str(getattr(event, name))
            row[name] = val 
        event_dict[str(event.timestamp)] = row
    batch = Local_Batch.objects.filter(batch_item__item__id=item.id)[0]
    for field in Local_Batch._meta.fields:
        name = field.name
        if name == 'batch_ptr':
            continue
        try:
            val = str(getattr(batch, name))
        except:
            val = getattr(batch, name)
        batch_dict[name] = val 
    problems = item.problem_set.all()
    for problem in problems:
        row = {}
        for field in Problem._meta.fields:
            name = field.name
            val = str(getattr(problem, name))
            row[name] = val 
        problem_dict[str(problem.time_reported)] = row 
    fedora_sites = item.fedora_sites.all()
    for fedora_site in fedora_sites:
        row = {}
        for field in fedora_site._meta.fields:
            name = field.name
            val = str(getattr(fedora_site, name))
            row[name] = val 
        fedora_site_dict[str(fedora_site.pid)] = row 
    fedora_collections = item.fedora_collections.all()
    for fedora_collection in fedora_collections:
        row = {}
        for field in fedora_collection._meta.fields:
            name = field.name
            val = str(getattr(fedora_collection, name))
            row[name] = val 
        fedora_collection_dict[str(fedora_collection.pid)] = row 
    object_dict['item'] = item_dict
    object_dict['item'] = item_dict
    object_dict['files'] = file_dict
    object_dict['events'] = event_dict
    object_dict['batch'] = batch_dict
    object_dict['problems'] = problem_dict
    object_dict['fedora_sites'] = fedora_site_dict
    object_dict['fedora_collections'] = fedora_collection_dict
    response = HttpResponse()
    json.dump(object_dict, response, sort_keys=True, indent=4)
    return response

def local_item(request, item_id):
    if request.method == 'POST': # update of an existing item
        local_item = Local_Item.objects.get(do_id=item_id)
        form = LocalItemForm(request.POST, instance=local_item)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('workflow.wflocal.views.local_item', args=[item_id]))
    else:
        item = Item.objects.get(do_id=item_id)
        local_item = Local_Item.objects.get(do_id=item_id)
        form = LocalItemForm(instance=local_item)
        t = loader.get_template('wflocal/local_item_form.html')
        c = RequestContext(request, {
            'item': item,
            'form': form,
        }) 
        return HttpResponse(t.render(c))



LIST_HEADERS = (
    ('Item ID', 'item__id'),
    ('name', 'item__name'),
    ('ready for', 'ready_action'),
    ('last action', 'last_transaction__description'),
    ('when', 'last_transaction__timestamp'),
    ('who', 'last_transaction__user__first_name'),
)

def get_facet_block(items_queryset, facet_fields, request):
    facet_block = {}
    for facet_field in facet_fields:
        this_facet_dict = {}
        # if there's currently a facet selected, add an option to clear
        if facet_field in request.GET.keys() and request.GET[facet_field]:
            this_query_dict = request.GET.copy()
            this_query_dict.__setitem__(facet_field, '')
            this_facet_dict['[clear selection]'] = this_query_dict.urlencode()
        # get the distinct values for this field in the queryset
        values_query_set = items_queryset.order_by().values(facet_field).distinct()
        for value_dict in values_query_set:
            this_value = value_dict[facet_field]
            # get the count of matching objects
            kwargs = { facet_field:this_value }
            count = items_queryset.filter(**kwargs).count()
            # get the label for the matching field value.  In order to handle related object fields
            # that would otherwise be id values, we do the __unicode__ method to get the name
            try:
                label = items_queryset.order_by().filter(**kwargs)[0].__getattribute__(facet_field).__unicode__()
            except:
                label = 'None'
            this_query_dict = request.GET.copy()
            this_query_dict.__setitem__(facet_field, this_value)
            key = '%s (%s)' % (label, count)
            this_facet_dict[key] = this_query_dict.urlencode()
        facet_block[facet_field] = this_facet_dict
    return facet_block


def sort_objects_by_name(objects):
    obj_dict = {}
    sorted_list = []
    for obj in objects:
        obj_dict[obj.name] = obj
    order = obj_dict.keys()
    order.sort()
    for o in order:
        sorted_list.append(obj_dict[o])
    return sorted_list

def sort_collections(objects):
    obj_dict = {}
    sorted_list = []
    for obj in objects:
        obj_dict[obj.c_id] = obj
    order = obj_dict.keys()
    order.sort()
    for o in order:
        sorted_list.append(obj_dict[o])
    return sorted_list

def sort_items(objects):
    obj_dict = {}
    sorted_list = []
    for obj in objects:
        obj_dict[obj.do_id] = obj
    order = obj_dict.keys()
    order.sort()
    for o in order:
        sorted_list.append(obj_dict[o])
    return sorted_list

def sort_objects_by_id(objects):
    obj_dict = {}
    sorted_list = []
    for obj in objects:
        obj_dict[obj.id] = obj
    order = obj_dict.keys()
    order.sort()
    for o in order:
        sorted_list.append(obj_dict[o])
    return sorted_list

def get_paged_items(items, request):
    paginator = Paginator(items, 25)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        return paginator.page(page)
    except (EmptyPage, InvalidPage):
        return paginator.page(paginator.num_pages)

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('workflow.wflocal.views.main'))

def item(request):
    items = Item.objects.all() 
    paged_items = get_paged_items(items, request)
    t = loader.get_template('wflocal/item.html')
    c = RequestContext(request, {
        'items': paged_items,
    })
    return HttpResponse(t.render(c))

def transaction():
    pass    

def item_detail(request, item_id):
    item = Local_Item.objects.get(do_id=item_id)
    item_form = Local_Item_Form(instance=item)
    transaction_list = item.transaction_set.all()
    status_list = Item_Actions_Status.objects.filter(item=item).order_by('order')
    coll_building_list = Collection_Building_Item_Status.objects.filter(item__item=item).order_by('order')
    problems_list = item.problem_set.all()
    file_list = Item_File.objects.filter(item=item).order_by('name')
    collections = Collection.objects.filter(collection_item__item__id=item.id) 
    batches = Batch.objects.filter(batch_item__item__id=item.id) 
    voyager_id = item.local_item.voyager_id
    t = loader.get_template('wflocal/item_detail.html')
    c = RequestContext(request, {
        'item': item,
        'item_form': item_form,
        'transaction_list': transaction_list,
        'status_list': status_list,
        'coll_building_list': coll_building_list,
        'file_list': file_list,
        'problems_list': problems_list,
        'batches': batches,
        'collections': collections,
    'voyager': voyager_id,
    })
    return HttpResponse(t.render(c))

def transactions(request):
    transactions = get_paged_items(Transaction.objects.order_by('timestamp').reverse(), request)
    t = loader.get_template('wflocal/transactions.html')
    c = RequestContext(request, { 'items': transactions, })
    return HttpResponse(t.render(c))

@login_required
def main(request):
    item_count = Item.objects.count()
    file_count = Item_File.objects.count()
    batch_count = Batch.objects.count()
    active_batch_count = Batch.objects.filter(active=True).count()
    coll_count = Collection.objects.count()    
    last_five_transactions = Transaction.objects.order_by('timestamp').reverse()[:5]
    t = loader.get_template('wflocal/main.html')
    c = RequestContext(request, {
    'items': item_count,
    'files': file_count,
    'batches': batch_count,
    'active_batches': active_batch_count,
    'colls': coll_count,
    'last_five': last_five_transactions,
    })
    return HttpResponse(t.render(c))

def reports(request):
    t = loader.get_template('wflocal/reports.html')
    c = RequestContext(request)
    return HttpResponse(t.render(c))

def admin(request):
    rebuilds = drlutils.collection_building.utils.get_textclass_colls_to_rebuild() 
    t = loader.get_template('wflocal/admin_menu.html')
    c = RequestContext(request, {
        'rebuilds': rebuilds,
    })
    return HttpResponse(t.render(c))

def batch_detail(request, batch_name, new="False", order='id'):
    try:
        batch = Local_Batch.objects.get(name=batch_name)
    except:
        batch = Batch.objects.get(name=batch_name)
    batch_form = Local_Batch_Form(instance=batch)
    f = ItemFilter(request.GET, queryset=Item_Current_Status.objects.filter(item__batch_item__batch=batch.id))
    actions = batch.get_item_actions() 
    problems = batch.get_problem_item_count() 
    paged_items = get_paged_items(f.qs, request)
    for p_i in paged_items.object_list:
        p_i.file_count = len(Item_File.objects.filter(item=p_i.item))
        if p_i.file_count > 0:
            p_i.first_file = Item_File.objects.filter(item=p_i.item).order_by('name')[0]
    t = loader.get_template('wflocal/batch_detail.html')
    c = RequestContext(request, {
        'batch': batch,
        'batch_form': batch_form,
        'new': new,
        'items': paged_items,
        'action_facet': actions,
        'problem_facet': problems,
        'filter': f,

    })
    return HttpResponse(t.render(c))

def collection(request):
    collections = sort_collections(Collection.objects.all()) 
    for c in collections:
        c.item_count = Collection_Item.objects.filter(collection=c).count()
        c.batch_count = Batch.objects.filter(collection=c).count()
        c.ready_actions = c.get_ready_actions() 
    t = loader.get_template('wflocal/collection.html')
    c = RequestContext(request, {
        'collections': collections,
    })
    return HttpResponse(t.render(c))


def collection_detail(request, collection_id, order='id'):
    collection = Collection.objects.get(c_id=collection_id)
    f = ItemFilter(request.GET, queryset=Item_Current_Status.objects.filter(item__collection_item__collection=collection))
    c_count = len(Collection_Item.objects.filter(collection=collection))
    actions = collection.get_item_actions() 
    problems = collection.get_problem_item_count() 
    paged_items = get_paged_items(f.qs, request)
    c_batches = Batch.objects.filter(collection=collection).order_by('-date')
    t = loader.get_template('wflocal/collection_detail.html')
    c = RequestContext(request, {
        'collection': collection,
        'items': paged_items,
        'c_count': c_count,
        'c_batches': c_batches,
        'action_facet': actions,
        'problem_facet': problems,
    })
    return HttpResponse(t.render(c))

def property_owner(request):
    property_owners = Property_Owner.objects.all() 
    t = loader.get_template('wflocal/property_owner.html')
    c = RequestContext(request, {
           'property_owners': property_owners,
   })
    return HttpResponse(t.render(c))

def property_owner_detail(request, property_owner_id):
    property_owner = Property_Owner.objects.get(pk=property_owner_id)
    items = Item.objects.filter(property_owner=property_owner_id)
    paged_items = get_paged_items(items, request)
    t = loader.get_template('wflocal/property_owner_detail.html')
    c = RequestContext(request, {
        'property_owner': property_owner,
        'items': paged_items,
    })
    return HttpResponse(t.render(c))


def item_type(request):
    item_types = Item_Type.objects.all() 
    t = loader.get_template('wflocal/item_type.html')
    c = RequestContext(request, {
           'item_types': item_types,
   })
    return HttpResponse(t.render(c))

def item_type_detail(request, item_type_id):
    item_type = Item_Type.objects.get(pk=item_type_id)
    items = Item.objects.filter(type=item_type_id)
    paged_items = get_paged_items(items, request)
    t = loader.get_template('wflocal/item_type_detail.html')
    c = RequestContext(request, {
        'item_type': item_type,
         'items': paged_items,
    })
    return HttpResponse(t.render(c))


def batch(request):
    try:
      batch = Batch.objects.get(name=request.GET['batch_name'])
      return HttpResponseRedirect(reverse('workflow.wflocal.views.batch_detail', args=(batch.id,)))
    except:
        if 'view' in request.GET.keys() and request.GET['view'] == 'all':
            f = BatchFilter(request.GET, queryset=Batch.objects.all().order_by('-date'))
        else:
            f = BatchFilter(request.GET, queryset=Batch.objects.filter(active=True).order_by('-date'))
        collection_facet = [] 
        type_facet = [] 
        property_owner_facet = [] 
        for batch in f.qs:
            try:
                collection_facet.append(Collection.objects.get(pk=batch.collection.id))
                type_facet.append(Item_Type.objects.get(pk=batch.type.id))
                property_owner_facet.append(Property_Owner.objects.get(pk=batch.property_owner.id))
            except:
                pass
            batch.ready_actions = batch.get_ready_actions() 
        collection_facet = sort_collections(set(collection_facet))
        type_facet = sort_objects_by_name(set(type_facet))
        property_owner_facet = sort_objects_by_name(set(property_owner_facet))
        t = loader.get_template('wflocal/batch.html')
        c = RequestContext(request, {
            'filter': f,
            'collection_facet': collection_facet,
            'type_facet': type_facet,
            'property_owner_facet': property_owner_facet,
        })
        return HttpResponse(t.render(c))


def batch_new(request):
    if request.method == 'POST':
        form = Local_Batch_Form(request.POST, request.FILES)
        if 'has_file' in request.POST.keys():
            form.fields['file'].required = True 
        if form.is_valid(): 
            batch = form.save()
            if 'has_file' in request.POST.keys():
                handle_local_csv_items(batch, request.FILES['file'])
            return HttpResponseRedirect('/django/workflow/batch/' + batch.name + '/success/') # Redirect after POST
    else:
        form = Local_Batch_Form()
    t = loader.get_template('wflocal/newbatch.html')
    c = RequestContext(request, { 'form' : form })
    return HttpResponse(t.render(c))



def sequence_list(request):
    seqs = Workflow_Sequence.objects.all().order_by('name')
    t = loader.get_template('wflocal/sequence_list.html')
    c = RequestContext(request, { 'seqs' : seqs })
    return HttpResponse(t.render(c))


def sequence_new(request): 
    if request.method == 'POST':
        form = SequenceForm(request.POST)
        if form.is_valid():
            create_sequence_from_form(form.cleaned_data)
            return HttpResponseRedirect(reverse('workflow.wflocal.views.sequence_list')) 
    else:
        form = SequenceForm()
    actions = Action.objects.all().order_by('name')
    t = loader.get_template('wflocal/sequence.html')
    c = RequestContext(request, { 'workflow_sequence_form' : form, 'actions' : actions })
    return HttpResponse(t.render(c))


def sequence_detail(request, sequence_id):
    if request.method == 'POST': # update of an existing sequence
        seq = Workflow_Sequence.objects.get(id=request.POST['this_id'])
        form = SequenceForm(request.POST, instance=seq)
        if form.is_valid():
            create_sequence_from_form(form.cleaned_data)
            return HttpResponseRedirect(reverse('workflow.wflocal.views.sequence_list')) 
    else:
        seq = Workflow_Sequence.objects.get(name=sequence_id)
        form = SequenceForm(instance=seq)
    form.fields['this_id'].initial = seq.id
    seq_actions = Workflow_Sequence_Actions.objects.filter(workflow_sequence=seq).order_by('order')
    actions = Action.objects.all().order_by('name')
    t = loader.get_template('wflocal/sequence.html')
    c = RequestContext(request, { 'workflow_sequence_form' : form, 'actions' : actions, 'sequence': seq, 'seq_actions' : seq_actions })
    return HttpResponse(t.render(c))


def setup_status_change(request):
    if request.method == 'POST':
        form = ChangeStatusSetupForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            complete = form.cleaned_data['complete']
            return HttpResponseRedirect('/django/workflow/status/change/' + str(action.id) + '/' + str(complete))
    else:
        form = ChangeStatusSetupForm()            
    
    t = loader.get_template('wflocal/status_change_setup.html')
    c = RequestContext(request, { 'form' : form })
    return HttpResponse(t.render(c))


def status_change(request, action, complete):
    item = None
    if request.method == 'POST':
        form = ChangeStatusForm(request.POST)
        if form.is_valid():
            item = Item.objects.get(do_id=form.cleaned_data['item'])
            user = User.objects.get(pk=request.POST['user'])
            act = Action.objects.get(pk=action)
            set_status(item, act, user, complete)
            form = ChangeStatusForm()
    else:
        form = ChangeStatusForm()            
    a = Action.objects.get(pk=action)
    t = loader.get_template('wflocal/status_change.html')
    c = RequestContext(request, { 'form' : form, 'action' : a, 'complete' : complete, 'item' : item })
    return HttpResponse(t.render(c))

def batch_active_change(request, batch_id):
    batch = Local_Batch.objects.get(id=batch_id)
    if batch.active:
        batch.active = False;
    else:
        batch.active = True;
    batch.save()
    return HttpResponseRedirect(reverse('workflow.wflocal.views.batch'))

def batch_status_change(request, batch_name):
    batch = Local_Batch.objects.get(name=batch_name)
    if request.method == 'POST':
        form = BatchChangeStatusForm(request.POST)
        if form.is_valid():
            action = Action.objects.get(pk=form.cleaned_data['action'])
            user = User.objects.get(pk=request.POST['user'])    
            complete = form.cleaned_data['complete']
            change_items = []
            if complete == 'True':    
                change_items = Item.objects.filter(batch_item__batch=batch, item_current_status__ready_action=action)
            elif complete == 'False':
                change_items = Item.objects.filter(batch_item__batch=batch, item_actions_status__action=action)
            for item in change_items:
                set_status(item, action, user, complete)
            return HttpResponseRedirect(reverse('workflow.wflocal.views.batch_detail', args=[str(batch.name)]))
    form = BatchChangeStatusForm()
    t = loader.get_template('wflocal/batch_status_change.html')
    c = RequestContext(request, { 'form' : form, 'batch' : batch, 'actions' : batch.get_item_actions() })
    return HttpResponse(t.render(c))

def batch_add_items(request, batch_name):    
    batch = Local_Batch.objects.get(name=batch_name)
    if request.method == 'POST':
        form = BatchFileForm(request.POST, request.FILES)
        if form.is_valid():
            handle_local_csv_items(batch, request.FILES['file'])
            return HttpResponseRedirect(reverse('workflow.wflocal.views.batch_detail', kwargs={ 'batch_name': batch_name, 'new': 'success'}))
    else:
        form = BatchFileForm()
    t = loader.get_template('wflocal/add_to_batch.html')
    c = RequestContext(request, { 'batch' : batch, 'form' : form })
    return HttpResponse(t.render(c))
    
def batch_add_single_item(request, batch_name):    
    batch = Local_Batch.objects.get(name=batch_name)
    if request.method == 'POST':
        item_form = Local_Item_To_Batch_Form(request.POST)
        if item_form.is_valid():
            new_item = item_form.save()
            handle_local_item_extras(new_item, batch) 
            if item_form.cleaned_data['item_files']:
                handle_files(new_item, item_form.cleaned_data['item_files'])
        if request.POST.has_key('_addanother'):
            return HttpResponseRedirect('/django/workflow/batch/' + batch_name + '/add_item/')
        else:
            return HttpResponseRedirect('/django/workflow/batch/' + batch_name + '/') 
    else:
        new_item = Local_Item()
        new_item.inherit_from_batch(batch)
        item_form = Local_Item_To_Batch_Form(instance=new_item)
    errors = ''
    t = loader.get_template('wflocal/add_single_item_to_batch.html')
    c = RequestContext(request, { 'batch' : batch, 'item_form' : item_form })
    return HttpResponse(t.render(c))

def status_ready(request, action):
    ics = Item_Current_Status.objects.filter(ready_action=action)
    json_serializer = serializers.get_serializer("json")()
    response = HttpResponse()
    json_serializer.serialize(ics, ensure_ascii=False, stream=response)
    return response

def problem_new(request, item_id):
    if request.method == 'POST':
        form = ReportProblemForm(request.POST)
        if form.is_valid():
            this_item = Item.objects.get(do_id=form.cleaned_data['item'])
            p = Problem(item=this_item, user_reported=request.user, description=form.cleaned_data['description'])
            p.save()
            record_transaction(None, this_item, request.user, 'preport')
            ics = Item_Current_Status.objects.get(item=this_item)
            ics.has_problem = True
            ics.save()
            return HttpResponseRedirect('/django/workflow/item/' + form.cleaned_data['item'])
    else: 
        item = Item.objects.get(do_id=item_id)
        form = ReportProblemForm()
    
    t = loader.get_template('wflocal/report_problem.html')
    c = RequestContext(request, { 'form' : form, 'item': item })
    return HttpResponse(t.render(c))


def problem_detail(request, problem_id):
    if request.method == 'POST':
        form = ProblemForm(request.POST)
        if form.is_valid() and form.cleaned_data['resolved']:    
            p = Problem.objects.get(pk=problem_id)
            p.resolved = True
            p.user_resolved = request.user
            p.notes_resolved = form.cleaned_data['notes_resolved']
            p.time_resolved = datetime.datetime.now()
            p.save()
            record_transaction(None, p.item, request.user, 'presolve')
            if Problem.objects.filter(item=p.item, resolved=False).count() == 0:
                ics = Item_Current_Status.objects.get(item=p.item)
                ics.has_problem = False
                ics.save()
            return HttpResponseRedirect('/django/workflow/item/' + p.item.do_id)

    p = Problem.objects.get(pk=problem_id)
    form = ProblemForm(instance=p)
    t = loader.get_template('wflocal/problem_detail.html')
    c = RequestContext(request, { 'form' : form, 'problem': p})
    return HttpResponse(t.render(c))

def item_file(request, item_id, file_name=None):
    if request.method == 'POST':
        form = ItemFileForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/django/workflow/item/' + item_id)
    else: 
        this_item = Item.objects.get(do_id=item_id)
        if file_name:
            item_file = Item_File.objects.get(item=this_item, name=file_name)
            form = ItemFileForm(instance=item_file)
        else:
            form = ItemFileForm({'item': this_item.id})
    t = loader.get_template('wflocal/item_file.html')
    c = RequestContext(request, { 'form' : form, 'item' : item_id })
    return HttpResponse(t.render(c))

