# XXX: json data used by this file are not stable
# they may evolve at any moment

import os
import itertools
from collections import defaultdict
from datetime import timedelta

from django.db import transaction
from django.core.files.base import ContentFile

from openPLM.plmapp.views.base import object_to_dict, get_obj_by_id
from openPLM.plmapp.models import DocumentFile, DelegationLink, Part, ROLE_OWNER, ROLE_NOTIFIED
from openPLM.plmapp.controllers import PartController
from openPLM.plmapp.references import get_new_reference
from openPLM.plmapp.tasks import update_indexes

from .models import Document3D, Document3DController, Location_link


# copy from a file generated by Open CASCADE
# product identifier/label placeholder are set line #7
_DECOMPOSED_STEP = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Open CASCADE Model'),'2;1');
FILE_NAME('Open CASCADE Shape Model','2013-04-03T15:08:20',('Author'),(
    'Open CASCADE'),'Open CASCADE STEP processor 6.3','Open CASCADE 6.3'
  ,'Unknown');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN_CC2 {{ 1 2 10303 214 -1 1 5 4 }}'));
ENDSEC;
DATA;
#1 = APPLICATION_PROTOCOL_DEFINITION('committee draft',
  'automotive_design',1997,#2);
#2 = APPLICATION_CONTEXT(
  'core data for automotive mechanical design processes');
#3 = SHAPE_DEFINITION_REPRESENTATION(#4,#10);
#4 = PRODUCT_DEFINITION_SHAPE('','',#5);
#5 = PRODUCT_DEFINITION('design','',#6,#9);
#6 = PRODUCT_DEFINITION_FORMATION('','',#7);
#7 = PRODUCT('{product}','{product}','',(#8));
#8 = MECHANICAL_CONTEXT('',#2,'mechanical');
#9 = PRODUCT_DEFINITION_CONTEXT('part definition',#2,'design');
#10 = SHAPE_REPRESENTATION('',(#11),#15);
#11 = AXIS2_PLACEMENT_3D('',#12,#13,#14);
#12 = CARTESIAN_POINT('',(0.,0.,0.));
#13 = DIRECTION('',(0.,0.,1.));
#14 = DIRECTION('',(1.,0.,-0.));
#15 = ( GEOMETRIC_REPRESENTATION_CONTEXT(3)
GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#19)) GLOBAL_UNIT_ASSIGNED_CONTEXT(
(#16,#17,#18)) REPRESENTATION_CONTEXT('Context #1',
  '3D Context with UNIT and UNCERTAINTY') );
#16 = ( LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.) );
#17 = ( NAMED_UNIT(*) PLANE_ANGLE_UNIT() SI_UNIT($,.RADIAN.) );
#18 = ( NAMED_UNIT(*) SI_UNIT($,.STERADIAN.) SOLID_ANGLE_UNIT() );
#19 = UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),#16,
  'distance_accuracy_value','confusion accuracy');
#20 = PRODUCT_TYPE('part',$,(#7));
ENDSEC;
END-ISO-10303-21;
"""


class AssemblyBuilder(object):

    def __init__(self, controller):
        self.controller = controller
        self.created_parts = []
        self.created_docs = []
        self.added_files = []
        self._updated_parts = set()
        self._files = [] # to delete files in case of an error
        self._parts = {}
        self._documents = {}
        self._inbulk_cache = {}
        # test if their will be at least one recipients
        self._send_mails = DelegationLink.current_objects.filter(delegator=controller._user,
                role__in=(ROLE_OWNER, ROLE_NOTIFIED)).exists()
        self._lock = False

    def build_assembly(self, tree, native_files, step_files, lock=False):
        self.controller.check_editable()
        self.controller.check_permission(ROLE_OWNER)
        self._lock = lock
        if self.controller.PartDecompose is not None:
            raise ValueError("Document is already decomposed")
        try:
            native = self._build(tree, native_files, step_files)
        except:
            # remove added files
            for path in self._files:
                os.remove(path)
            raise
        return native

    @transaction.commit_on_success
    def _build(self, tree, native_files, step_files):
        # tasks (handle_step_files, update_indexes) are executed
        # once the transaction is commited, so we do not have to
        # block mails and indexing
        # all instances are indexing by one task to avoid a lot of lock/unlock
        # calls
        self._native_files = dict((f.name.lower(), f) for f in native_files)
        self._step_files = dict((f.name.lower(), f) for f in step_files)
        self.controller.object.no_index = True
        if not self._send_mails:
            self.controller.block_mails()
        name = self._get_part_name(tree)
        self.root = self._add_part(self.controller, name)
        if tree["children"]:
            self._add_decomposed_step(self.controller, name)
            self._add_children(self.root, tree)
        else:
            self._add_step_file(self.controller, tree)
        # native files are added after step files and PCL
        # so that it is easier to test if it is possible to checkout a whole
        # assembly using native files
        native = self._add_native_file(self.controller, tree)
        # indexes all parts, documents and files
        updated = itertools.chain(self.created_parts, self.created_docs, self.added_files)
        update_indexes.delay([(c._meta.app_label, c._meta.module_name, c.pk) for c in updated])
        return native

    def update_assembly(self, tree, native_files, step_files, lock=False):
        self.controller.check_editable()
        self.controller.check_permission(ROLE_OWNER)
        self._lock = lock
        if self.controller.PartDecompose is None:
            raise ValueError("Document is not decomposed")
        try:
            native = self._update(tree, native_files, step_files)
        except:
            # remove added files
            for path in self._files:
                os.remove(path)
            raise
        return native

    @transaction.commit_on_success
    def _update(self, tree, native_files, step_files):
        # tasks (handle_step_files, update_indexes) are executed
        # once the transaction is commited, so we do not have to
        # block mails and indexing
        # all instances are indexing by one task to avoid a lot of lock/unlock
        # calls
        self._native_files = dict((f.name.lower(), f) for f in native_files)
        self._step_files = dict((f.name.lower(), f) for f in step_files)
        self.controller.object.no_index = True
        if not self._send_mails:
            self.controller.block_mails()
        self.root = self._get_part(tree)
        if tree["children"]:
            self._checkin_decomposed_step(self.controller, tree)
            self._update_children(self.root, tree)
        else:
            self._checkin_step(self.controller, tree)
        # native files are added after step files and PCL
        # so that it is easier to test if it is possible to checkout a whole
        # assembly using native files
        native = self._checkin_native(self.controller, tree)
        # indexes all parts, documents and files
        updated = itertools.chain(self.created_parts, self.created_docs, self.added_files)
        update_indexes.delay([(c._meta.app_label, c._meta.module_name, c.pk) for c in updated])
        return native

    def _get_native_docfile(self, node):
        df_id = node["native"]["id"]
        return DocumentFile.objects.get(id=df_id)

    def _get_step_docfile(self, node):
        df_id = node["step"]["id"]
        return DocumentFile.objects.get(id=df_id)

    def _checkin_decomposed_step(self, doc, node):
        # just add a new revision with the same content
        df = self._get_step_docfile(node)
        fake_file = ContentFile(df.file.read())
        fake_file.name = df.filename
        # no thumbnail
        doc.checkin(df, fake_file, True, False)
        self.added_files.append(df)
        self._files.append(df.file.path)
        if self._lock:
            doc.lock(df)

    def _checkin_native(self, doc, node):
        df = self._get_native_docfile(node)
        filename = df.filename.lower()
        doc.checkin(df, self._native_files[filename])
        self.added_files.append(df)
        self._files.append(df.file.path)
        if self._lock:
            doc.lock(df)
        return df

    def _checkin_step(self, doc, node):
        df = self._get_step_docfile(node)
        filename = df.filename.lower()
        doc.checkin(df, self._step_files[filename])
        self.added_files.append(df)
        self._files.append(df.file.path)
        if self._lock:
            doc.lock(df)

    def _get_part(self, node):
        part_id = node["part"]["id"]
        try:
            part = self._parts[part_id]
        except KeyError:
            part = get_obj_by_id(part_id, self.controller._user)
            part.check_readable()
            # indexed content is up to date, indexed attributes are not modified
            part.object.no_index = True
            self._parts[part_id] = part
        return part

    def _get_doc(self, node):
        doc_id = node["document"]["id"]
        try:
            doc = self._documents["id"]
        except KeyError:
            doc = get_obj_by_id(doc_id, self.controller._user)
            if doc.type != "Document3D":
                raise ValueError("invalid document")
            doc.check_readable()
            # indexed content is up to date, indexed attributes are not modified
            doc.object.no_index = True
            self._documents[doc_id] = doc
        return doc

    def _get_part_name(self, node):
        name = node["part_name"].strip()
        if not name:
            raise ValueError("Invalid part name")
        return name

    def _add_doc(self, name):
        data = {
            "lifecycle": self.controller.lifecycle,
            "group": self.controller.group,
            "name": name,
        }
        ref = get_new_reference(self.controller._user, Document3D,
                                len(self.created_docs), self._inbulk_cache)
        doc = Document3DController.create(ref, "Document3D", "a", self.controller._user,
                data, not self._send_mails, True)
        self.created_docs.append(doc)
        # it is not useful to send history mails saying a file has been added
        # ot that a part has been attached
        if self._send_mails:
            doc.block_mails()
        return doc

    def _add_part(self, doc, name):
        data = {
            "lifecycle": self.controller.lifecycle,
            "group": self.controller.group,
            "name": name,
        }
        ref = get_new_reference(self.controller._user, Part,
                                len(self.created_parts), self._inbulk_cache)
        part = PartController.create(ref, "Part", "a", self.controller._user, data,
                not self._send_mails, True)
        self._parts[name] = part
        self._parts[part.id] = part
        doc.attach_to_part(part)
        doc.object.PartDecompose = part.object
        doc.object.save()
        self.created_parts.append(part)
        if self._send_mails:
            part.block_mails()
        return part

    def _add_native_file(self, doc, node):
        filename = node["native"].lower()
        df = doc.add_file(self._native_files[filename])
        self.added_files.append(df)
        self._files.append(df.file.path)
        return df

    def _add_step_file(self, doc, node):
        filename = node["step"].lower()
        # the thumbnail is generated by handle_step_file
        df = doc.add_file(self._step_files[filename], True, False)
        self.added_files.append(df)
        self._files.append(df.file.path)
        if self._lock:
            doc.lock(df)
        return df

    def _add_decomposed_step(self, doc, name):
        # use name as product identifier/label
        product = name.replace("\\", "\\\\").replace("'", "\\'").encode("latin-1")
        fake_file = ContentFile(_DECOMPOSED_STEP.format(product=product))
        fake_file.name = name + ".step"
        # no thumbnail
        df = doc.add_file(fake_file, True, False)
        self.added_files.append(df)
        self._files.append(df.file.path)
        if self._lock:
            doc.lock(df)
        return df

    def _add_children(self, parent, node):
        children = defaultdict(list)
        for child in node["children"]:
            name = self._get_part_name(child)
            try:
                part = self._parts[name]
            except KeyError:
                doc = self._add_doc(name)
                part = self._add_part(doc, name)
                if child["children"]:
                    self._add_children(part, child)
                    self._add_decomposed_step(doc, name)
                else:
                    self._add_step_file(doc, child)
                self._add_native_file(doc, child)
            children[part].append((child["local_name"].strip(), child["local_matrix"]))

        # parent child link
        for order, (part, locations) in enumerate(children.iteritems(), 1):
            quantity = len(locations)
            pcl = parent.add_child(part, quantity, order)
            for local_name, matrix in locations:
                if not local_name:
                    local_name = part.name
                pcle = Location_link(name=local_name, link=pcl)
                (pcle.x1, pcle.x2, pcle.x3, pcle.x4,
                    pcle.y1, pcle.y2, pcle.y3, pcle.y4,
                    pcle.z1, pcle.z2, pcle.z3, pcle.z4) = matrix
                pcle.save()

    def _update_children(self, parent, node):
        if parent.id in self._updated_parts:
            return
        self._updated_parts.add(parent.id)
        current_children = parent.get_children(1)
        children = defaultdict(list)
        for child in node["children"]:
            try:
                # existing part
                part = self._get_part(child)
            except KeyError:
                # new part
                name = self._get_part_name(child)
                try:
                    part = self._parts[name]
                except KeyError:
                    doc = self._add_doc(name)
                    part = self._add_part(doc, name)
                    if child["children"]:
                        self._update_children(part, child)
                        self._add_decomposed_step(doc, name)
                    else:
                        self._add_step_file(doc, child)
                    self._add_native_file(doc, child)
            else:
                if part.id not in self._updated_parts:
                    doc = self._get_doc(child)
                    if doc.PartDecompose.id != part.id:
                        raise ValueError("Invalid pair of part/document")
                    if child["document"]["checkin"]:
                        if child["children"]:
                            self._checkin_decomposed_step(doc, child)
                            self._update_children(part, child)
                        else:
                            self._checkin_step(doc, child)
                        self._checkin_native(doc, child)
            self._updated_parts.add(part.id)
            children[part.id].append((child["local_name"].strip(), child["local_matrix"]))

        order = 0
        for level, link in current_children:
            order = max(order, link.order)
            if link.child_id in children:
                # child has new locations
                locations = children[link.child_id]
                quantity = len(locations)
                new_link = parent.modify_child(link.child, quantity, link.order, link.unit,
                        location=None)
                # delete locations cloned by modify_child
                Location_link.objects.filter(link=new_link).delete()
                self._add_locations(new_link, locations)
                del children[link.child_id]
            else:
                extensions = link.extensions
                if any(isinstance(ext, Location_link) for ext in extensions):
                    # child has been removed
                    parent.delete_child(link.child)
        order += 1

        # new parts
        for order, (part_id, locations) in enumerate(children.iteritems(), order):
            quantity = len(locations)
            part = self._parts[part_id]
            pcl = parent.add_child(part, quantity, order)
            self._add_locations(pcl, locations)

    def _add_locations(self, pcl, locations):
        for local_name, matrix in locations:
            if not local_name:
                local_name = pcl.child.name
            pcle = Location_link(name=local_name, link=pcl)
            (pcle.x1, pcle.x2, pcle.x3, pcle.x4,
                pcle.y1, pcle.y2, pcle.y3, pcle.y4,
                pcle.z1, pcle.z2, pcle.z3, pcle.z4) = matrix
            pcle.save()


class AssemblyInfo(object):

    def __init__(self, controller):
        self.controller = controller
        self.user = self.controller._user
        self._allowed_checkout = "step,native"
        self._documents = {}
        self._parts = {}

    def get_assembly_info(self):
        root = self.controller.PartDecompose
        component = self._get_component(self.controller.object, root)
        if root is None:
            component["part"] = None
        else:
            self._add_children(component, root)
        # files
        info = {
            "component": component,
            "documents": self._documents,
            "parts": self._parts,
            "checkout": self._allowed_checkout,
        }
        return info

    def _get_component(self, doc, part):
        Document3DController(doc, self.user).check_readable()
        component = {}
        component["document"] = doc.id
        draft = doc.is_draft
        if doc.id not in self._documents:
            d = self._documents[doc.id] = object_to_dict(doc)
            files = d["files"] = []
            for df in doc.files:
                checkout = draft and (not df.locked) and df.checkout_valid
                files.append({
                    "id": df.id,
                    "filename": df.filename,
                    "size": df.size,
                    "locked": df.locked,
                    "locker": getattr(df.locker, "username", None),
                    "checkout": checkout,
                    "ctime": df.ctime,
                })
        if part is not None:
            component["part"] = part.id
            if part.id not in self._parts:
                self._parts[part.id] = object_to_dict(part)
        else:
            component["part"] = None
        component["children"] = []
        return component

    def _add_children(self, component, root):
        pctrl = PartController(root, self.user)
        pctrl.check_readable()
        children = pctrl.get_children(-1)
        if not children:
            return

        components = { root.id: component, }
        links = [c.link for c in children]
        locations = defaultdict(list) # pcl -> locations
        for loc in Location_link.objects.filter(link__in=links):
            locations[loc.link_id].append(loc)
        parts = [l.child_id for l in links]
        part2doc = {}
        for doc in Document3D.objects.filter(PartDecompose__in=parts):
            key = doc.PartDecompose_id
            # if two revisions are present, takes the newest one
            otherdoc = part2doc.get(key)
            if otherdoc is None or otherdoc.ctime < doc.ctime:
                part2doc[key] = doc

        visited_links = set()
        mtime = root.ctime
        for link in links:
            if link.id in visited_links:
                pass
            try:
                comp = components[link.parent_id]
                part = link.child
                doc = part2doc[part.id]
                locs = locations[link.id]
            except KeyError:
                # it is not an interessing link
                pass
            else:
                mtime = max(mtime, link.ctime)
                child_comp = self._get_component(doc, part)
                locs = [{"local_name": l.name, "local_matrix": l.to_array()} for l in locs]
                comp["children"].append({
                    "component": child_comp,
                    "locations": locs,
                })
                components[part.id] = child_comp
                visited_links.add(link.id)

        self._allowed_checkout = self._get_checkout(mtime)

    def _get_checkout(self, bom_mtime):
        tolerance = timedelta(seconds=60)
        bom_mtime -= tolerance
        for doc in self._documents.itervalues():
            for f in doc["files"]:
                ctime = f["ctime"]
                name, ext = os.path.splitext(f["filename"])
                name = name.lower()
                if ctime < bom_mtime:
                    return "step"
                elif ext.lower() in (".step", ".stp"):
                    native = [df for df in doc["files"] if df["id"] != f["id"]
                                 and df["filename"].lower().startswith(name + ".")]
                    if native:
                        if any(n["ctime"] < ctime - tolerance for n in native):
                            return "step"
                    else:
                        return "step"
        return "step,native"


def get_assembly_info(document):
    ai = AssemblyInfo(document)
    return ai.get_assembly_info()
