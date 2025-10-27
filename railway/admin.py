from django.contrib import admin

from railway.models import (
    Station,
    Route,
    Crew,
    Trip,
    TrainType,
    Train,
    Order,
    Ticket,
)

admin.site.register(Station)
admin.site.register(Route)
admin.site.register(Crew)
admin.site.register(Trip)
admin.site.register(TrainType)
admin.site.register(Train)
admin.site.register(Order)
admin.site.register(Ticket)
