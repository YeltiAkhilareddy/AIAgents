from .models import Prompt
from .models import TicketAssignment
from rest_framework import serializers
from .models import Ticket, Category, Module, Team
from users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class CategorySerializerK(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['category_id', 'name', 'description']


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'name', 'description']


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'


class TicketAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketAssignment
        fields = [
            'ticket_assignment_id', 'ticket', 'assigned_to', 'status',
            'comments', 'assigned_at'
        ]
        read_only_fields = ['ticket_assignment_id', 'assigned_at']


class TicketAssignmentSerializerK(serializers.ModelSerializer):
    assigned_to_name = serializers.ReadOnlyField(
        source='assigned_to.name')

    class Meta:
        model = TicketAssignment
        fields = [
            'ticket_assignment_id', 'assigned_to', 'assigned_to_name', 'status',
            'comments', 'assigned_at'
        ]


class TicketSerializerK(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    module_name = serializers.ReadOnlyField(source='module.name')
    assignments = TicketAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'ticket_id', 'title', 'description', 'priority', 'project_type',
            'status', 'created_at', 'updated_at', 'user', 'module', 'module_name',
            'project', 'category', 'category_name', 'assignments'
        ]


class PromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prompt
        fields = ['id', 'name', 'content', 'created_at', 'updated_at']
