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


class TicketInLine(admin.TabularInline):
    model = Ticket
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = (TicketInLine,)


admin.site.register(Station)
admin.site.register(Route)
admin.site.register(Crew)
admin.site.register(Trip)
admin.site.register(TrainType)
admin.site.register(Train)
admin.site.register(Ticket)
