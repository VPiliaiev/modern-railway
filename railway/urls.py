from django.urls import path, include
from rest_framework import routers

from railway.views import (
    StationViewSet,
    RouteViewSet,
    CrewViewSet,
    TripViewSet,
    TrainTypeViewSet,
    TrainViewSet,
    OrderViewSet,
)

app_name = "railway"
router = routers.DefaultRouter()
router.register("stations", StationViewSet)
router.register("routes", RouteViewSet)
router.register("crews", CrewViewSet)
router.register("trips", TripViewSet)
router.register("train-types", TrainTypeViewSet)
router.register("trains", TrainViewSet)
router.register("orders", OrderViewSet)
urlpatterns = [path("", include(router.urls))]
