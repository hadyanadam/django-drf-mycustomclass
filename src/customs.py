from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from django.utils.decorators import classonlymethod
from functools import update_wrapper
from django.views.decorators.csrf import csrf_exempt
#MULTIPLE POST DATA WITH LIST
class MultipleCreateAPIView(CreateAPIView):
    def create(self, request, *args, **kwargs):
        model = getattr(self.serializer_class.Meta,'model')
        is_multiple = isinstance(request.data,list)
        serializer = self.get_serializer(data=request.data, many=is_multiple)
        serializer.is_valid(raise_exception=True)
        if is_multiple:
            obj_created = []
            for list_inv in request.data:
                obj         = model.objects.create(**list_inv)
                obj_created.append(obj.id)
            results = model.objects.filter(id__in=obj_created)
            output_serializer = self.serializer_class(results, many=True)
            data = output_serializer.data[:]
            headers = self.get_success_headers(output_serializer.data)
        else:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            data = serializer.data
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

class DataPointFilterView(ModelViewSet):
    @classonlymethod
    def as_view(cls, actions={"get":"list"}, **initkwargs):
        cls.name = None
        cls.description = None
        cls.suffix = None
        cls.detail = None
        cls.basename = None

        if not actions:
            raise TypeError("The `actions` argument must be provided when "
                            "calling `.as_view()` on a ViewSet. For example "
                            "`.as_view({'get': 'list'})`")

        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError("You tried to pass in the %s method name as a "
                                "keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError("%s() received an invalid keyword %r" % (
                    cls.__name__, key))

        if 'name' in initkwargs and 'suffix' in initkwargs:
            raise TypeError("%s() received both `name` and `suffix`, which are "
                            "mutually exclusive arguments." % (cls.__name__))

        def view(request, *args, **kwargs):
            self = cls(**initkwargs)
            self.action_map = actions

            for method, action in actions.items():
                handler = getattr(self, action)
                setattr(self, method, handler)

            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get

            self.request = request
            self.args = args
            self.kwargs = kwargs

            return self.dispatch(request, *args, **kwargs)

        update_wrapper(view, cls, updated=())

        update_wrapper(view, cls.dispatch, assigned=())

        view.cls = cls
        view.initkwargs = initkwargs
        view.actions = actions
        return csrf_exempt(view)

    def get_queryset(self, *args, **kwargs):
        assert self.queryset is not None, (
            "'%s' should either include a `queryset` attribute, "
            "or override the `get_queryset()` method."
            % self.__class__.__name__
        )

        queryset = self.queryset
        return queryset

    def get_range_query_params(self, *args, **kwargs):
        assert self.request.query_params.get('range_start',None) is not None, (
            "query params range start not found "
        )

        assert self.request.query_params.get('range_end',None) is not None, (
            "query params range end not found"
        )
        query_params = {}
        query_params["range_start"] = self.request.query_params.get('range_start',None)
        query_params["range_end"] = self.request.query_params.get('range_end',None)
        return query_params

    def get_data_point_query_params(self, *args, **kwargs):
        assert self.request.query_params.get('data_point',None) is not None, (
            "query params range end not found"
        )
        query_params = self.request.query_params.get('data_point', None)
        return query_params

    def get_object(self, *args, **kwargs):
        queryset = self.get_queryset()
        try:
            query_params = self.get_range_query_params()
            range_start = query_params["range_start"]
            range_end = query_params["range_end"]
        except AssertionError:
            range_start = None
            range_end = None
        if range_start is not None and range_end is not None:
            obj = queryset.objects.filter(time_stamp__gte=range_start, time_stamp__lte=range_end)
            return obj
        return None

    def list(self, *args, **kwargs):
        try:
            data_point = self.get_data_point_query_params()
        except AssertionError:
            data_point = None
        obj = self.get_object()
        json_res = {}
        json_list = []
        if obj is not None:
            if data_point is not None:
                prevobj = obj[0]
                totalEnergy= obj[0].energy
                indexPoint = 0
                extraString = ""
                if data_point == "hourly":
                    indexPoint = 11
                    extraString = '0000' + prevobj.time_stamp[19:]
                elif data_point == "daily":
                    indexPoint = 8
                    extraString = prevobj.time_stamp[19:]
                elif data_point == "realtime":
                    serializer = self.get_serializer(obj, many=True)
                    return Response(serializer.data)
                else:
                    return Response({"error" : "data point parameter is not correct please enter the correct value eg. hourly, daily, realtime"}, status=400)
                prevDataPoint = obj[0].time_stamp[:indexPoint]
                for count, data in enumerate(obj):
                    if prevDataPoint == data.time_stamp[:indexPoint]:
                        totalEnergy += data.energy
                    if prevDataPoint != data.time_stamp[:indexPoint] or count == (len(obj) - 1):
                        json_res['time_stamp'] = prevobj.time_stamp[:indexPoint] + extraString
                        json_res['serial_number'] = prevobj.serial_number
                        json_res['energy'] = round(totalEnergy,2)
                        json_list.append(json_res)
                        json_res = {}
                        totalEnergy = data.energy
                    prevDataPoint = data.time_stamp[:indexPoint]
                    prevobj = data
                return Response(json_list, status=200)
            return Response({"error": "'data point' in url parameter not found"}, status=400)
        return Response({"error": "url parameter not found or wrong format"},status=400)
