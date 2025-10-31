from django.utils.dateparse import parse_date
from rest_framework import viewsets
from railway.models import (
    Station,
    Route,
    Crew,
    Trip,
    TrainType,
    Train,
    Order,
    Ticket
)
from railway.serializers import (
    StationSerializer,
    RouteSerializer,
    CrewSerializer,
    TripSerializer,
    TrainTypeSerializer,
    TrainSerializer,
    OrderSerializer,
    TicketSerializer, TripListSerializer, TripRetrieveSerializer
)


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer


class CrewViewSet(viewsets.ModelViewSet):
    queryset = Crew.objects.all()
    serializer_class = CrewSerializer


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all().select_related(
        "train",
        "route__source",
        "route__destination"
    ).prefetch_related("crew")

    def get_serializer_class(self):
        if self.action == "list":
            return TripListSerializer
        elif self.action == "retrieve":
            return TripRetrieveSerializer
        return TripSerializer

    @staticmethod
    def _param_to_str(query_string):
        return [s.strip() for s in query_string.split(",") if s.strip()]

    @staticmethod
    def _param_to_date(query_string):
        return parse_date(query_string)

    def get_queryset(self):
        queryset = self.queryset

        source = self.request.query_params.get("source")
        destination = self.request.query_params.get("destination")
        date = self.request.query_params.get("date")

        if source:
            queryset = queryset.filter(route__source__name__icontains=source.strip())

        if destination:
            queryset = queryset.filter(route__destination__name__icontains=destination.strip())

        if date:
            date_parsed = self._param_to_date(date)
            if date_parsed:
                queryset = queryset.filter(departure_time__date=date_parsed)

        return queryset.order_by("departure_time")


class TrainTypeViewSet(viewsets.ModelViewSet):
    queryset = TrainType.objects.all()
    serializer_class = TrainTypeSerializer


class TrainViewSet(viewsets.ModelViewSet):
    queryset = Train.objects.all()
    serializer_class = TrainSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
