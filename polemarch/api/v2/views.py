# pylint: disable=unused-argument,protected-access,too-many-ancestors
from collections import OrderedDict
from django.http import HttpResponse
from rest_framework import exceptions as excepts
from rest_framework.authtoken import views as token_views
from vstutils.api.permissions import StaffPermission
from vstutils.api import base, views
from vstutils.utils import KVExchanger

from . import filters
from . import serializers
from ..base import PermissionMixin, LimitedPermissionMixin
from ...main import utils


class __VarsViewSet(base.ModelViewSetSet):
    model = serializers.models.Variable
    serializer_class = serializers.VariableSerializer
    filter_class = filters.VariableFilter


@base.nested_view('variables', 'id', view=__VarsViewSet)
class _VarsMixin(base.ModelViewSetSet):
    '''
    Instance variables view.
    '''


class TokenView(token_views.ObtainAuthToken):
    def delete(self, request, *args, **kwargs):
        token = request.auth
        if token:
            key = token.key
            token.delete()
            return base.Response("Token {} removed.".format(key), 204).resp
        raise excepts.ParseError("Token not found.")


class UserViewSet(views.UserViewSet):
    serializer_class = serializers.UserSerializer
    serializer_class_one = serializers.OneUserSerializer

    @base.action(methods=["post", "delete", "get"], url_path="settings", detail=True)
    def user_settings(self, request, *args, **kwargs):
        obj = self.get_object()
        method = request.method
        if method != "GET":
            obj.settings.data = request.data if method == "POST" else {}
            obj.settings.save()
        return base.Response(obj.settings.data, 200).resp


class TeamViewSet(PermissionMixin, base.ModelViewSetSet):
    model = serializers.models.UserGroup
    serializer_class = serializers.TeamSerializer
    serializer_class_one = serializers.OneTeamSerializer
    filter_class = filters.TeamFilter

    def get_extra_queryset(self):
        return self.queryset


class HistoryViewSet(LimitedPermissionMixin, base.HistoryModelViewSet):
    model = serializers.models.History
    serializer_class = serializers.HistorySerializer
    serializer_class_one = serializers.OneHistorySerializer
    filter_class = filters.HistoryFilter
    POST_WHITE_LIST = ['cancel']

    @base.action(methods=["get"], detail=True)
    def raw(self, request, *args, **kwargs):
        result = self.get_serializer(self.get_object()).get_raw(request)
        return HttpResponse(result, content_type="text/plain")

    @base.action(methods=["get"], detail=True)
    def lines(self, request, *args, **kwargs):
        return self.get_paginated_route_response(
            self.get_object().raw_history_line.all().cleared(),
            serializers.HistoryLinesSerializer,
            filters.HistoryLinesFilter
        )

    @base.action(methods=["post"], detail=True)
    def cancel(self, request, *args, **kwargs):
        obj = self.get_object()
        exch = KVExchanger(utils.CmdExecutor.CANCEL_PREFIX + str(obj.id))
        exch.send(True, 10)
        return base.Response("Task canceled: {}".format(obj.id), 200).resp

    @base.action(methods=["get"], detail=True)
    def facts(self, request, *args, **kwargs):
        objs = self.get_serializer(self.get_object()).get_facts(request)
        return base.Response(objs, 200).resp

    @base.action(methods=["delete"], detail=True)
    def clear(self, request, *args, **kwargs):
        default_message = "Output trancated.\n"
        obj = self.get_object()
        if obj.status in ["RUN", "DELAY"] or obj.raw_stdout == default_message:
            raise excepts.NotAcceptable(
                "Job is running or already trancated"
            )
        obj.raw_stdout = default_message
        result = self.get_serializer(obj).get_raw(request)
        return base.Response(result, 204).resp


class HostViewSet(_VarsMixin, PermissionMixin):
    model = serializers.models.Host
    serializer_class = serializers.HostSerializer
    serializer_class_one = serializers.OneHostSerializer
    filter_class = filters.HostFilter


class _BaseGroupViewSet(_VarsMixin):
    model = serializers.models.Group
    serializer_class = serializers.GroupSerializer
    serializer_class_one = serializers.OneGroupSerializer
    filter_class = filters.GroupFilter


@base.nested_view(
    'host', 'id', manager_name='hosts', allow_append=True, view=HostViewSet
)
@base.nested_view(
    'group', 'id', manager_name='groups', allow_append=True, view=_BaseGroupViewSet
)
class _GroupMixin(_VarsMixin):
    '''
    Instance with groups and hosts.
    '''


class GroupViewSet(_BaseGroupViewSet, _GroupMixin, PermissionMixin):

    def nested_allow_check(self):
        if not self.nested_parent_object.children and self.nested_name == 'group':
            raise excepts.ValidationError("Group is not children.")
        if self.nested_parent_object.children and self.nested_name == 'host':
            raise excepts.ValidationError("Group is children.")


@base.nested_view(
    'all_groups', 'id', manager_name='groups_list', methods=['get'], view=GroupViewSet
)
@base.nested_view('all_hosts', 'id', methods=['get'], view=HostViewSet)
class InventoryViewSet(_GroupMixin, PermissionMixin):
    model = serializers.models.Inventory
    serializer_class = serializers.InventorySerializer
    serializer_class_one = serializers.OneInventorySerializer
    filter_class = filters.InventoryFilter


class __PlaybookViewSet(base.ModelViewSetSet):
    lookup_field = 'id'
    model = serializers.models.Task
    serializer_class = serializers.PlaybookSerializer
    serializer_class_one = serializers.OnePlaybookSerializer
    filter_class = filters.TaskFilter


class __PeriodicTaskViewSet(_VarsMixin, LimitedPermissionMixin):
    lookup_field = 'id'
    model = serializers.models.PeriodicTask
    serializer_class = serializers.PeriodictaskSerializer
    serializer_class_one = serializers.OnePeriodictaskSerializer
    filter_class = filters.PeriodicTaskFilter
    POST_WHITE_LIST = ['execute']

    @base.action(methods=["post"], detail=True)
    def execute(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return serializer.execute().resp


@base.nested_view(
    'inventory', 'id', manager_name='inventories', allow_append=True,
    view=InventoryViewSet
)
@base.nested_view(
    'playbook', 'id', manager_name='tasks', allow_append=True,
    view=__PlaybookViewSet, methods=['get']
)
@base.nested_view(
    'periodic_task', 'id', manager_name='periodic_tasks', allow_append=True,
    view=__PeriodicTaskViewSet, subs=['execute']
)
@base.nested_view(
    'history', 'id', manager_name='history',
    view=HistoryViewSet, subs=['raw', 'lines', 'cancel', 'facts', 'clear']
)
class ProjectViewSet(_GroupMixin, PermissionMixin):
    model = serializers.models.Project
    serializer_class = serializers.ProjectSerializer
    serializer_class_one = serializers.OneProjectSerializer
    filter_class = filters.ProjectFilter
    POST_WHITE_LIST = ['sync', 'execute_playbook', 'execute_module']

    @base.action(
        methods=["get"], url_path="supported-repos",
        detail=False, serializer_class=serializers.EmptySerializer
    )
    def supported_repos(self, request):
        return base.Response(self.model.repo_handlers.keys(), 200).resp

    @base.action(
        methods=["post"], detail=True, serializer_class=serializers.EmptySerializer
    )
    def sync(self, request, *args, **kwargs):
        return self.get_serializer(self.get_object()).sync().resp

    @base.action(methods=["post"], url_path="execute-playbook", detail=True)
    def execute_playbook(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return serializer.execute_playbook(request).resp

    @base.action(methods=["post"], url_path="execute-module", detail=True)
    def execute_module(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return serializer.execute_module(request).resp


class BulkViewSet(views.BulkViewSet):
    pass
