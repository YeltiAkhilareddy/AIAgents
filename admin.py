from django.contrib import admin
from .models import Ticket, Category, Message, Team, TicketAssignment, Module

# Register your models here.
admin.site.register(Ticket)
admin.site.register(Category)
admin.site.register(Message)
admin.site.register(Team)
admin.site.register(TicketAssignment)
admin.site.register(Module)
