import os
from collections import defaultdict
from .utils import fetch_cleaned_json, process_ticket_assignments, send_sla_breach_notifications
from rest_framework.decorators import api_view
from datetime import datetime

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.timezone import now

from rest_framework import status, viewsets
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

import boto3
import requests
import json
import re

from .models import (
    Prompt,
    ChatConvo,
    Ticket,
    TicketAssignment,
    Team,
    Category,
    Module,
)
from presalesApp.models import Project
from users.models import User

from .serializers import (
    PromptSerializer,
    TicketSerializer,
    TicketAssignmentSerializer,
    CategorySerializer,
    CategorySerializerK,
    TeamSerializer,
    ModuleSerializer,
)

from .utils import (
    Response_Agent_function,
    create_sap_ticket_from_context_Experimentals,
    fetch_excel_from_s3,
    fetch_memory_contexts,
    get_ai_responses,
    get_suitable_team,
    postprocess_tickets,
    process_ticket_response,
    serial_number_exists_in_excel,
    track_serial_number,
    validate_fetch_excel_from_s3,
    validate_serial_number_exists_in_excel,
    validate_extract_text_from_excel,
    validate_track_serial_number

)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class TicketViewSet(viewsets.ModelViewSet):

    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

    def list(self, request):
        tickets = self.get_queryset().select_related('user', 'category')

        response_data = []
        for ticket in tickets:
            response_data.append({
                "ticket_id": ticket.ticket_id,
                "title": ticket.title,
                "description": ticket.description,
                "status": ticket.status,
                "priority": ticket.priority,
                "type": ticket.type,
                "created_at": ticket.created_at,
                "updated_at": ticket.updated_at,
                "resolved_at": ticket.resolved_at,
                "user_name": ticket.user.name,
                "category_name": ticket.category.name,
            })
        return Response(response_data)

    def create(self, request, *args, **kwargs):
        data = request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "message": "Ticket created successfully",
                "ticket": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class CategoryAPIView(APIView):
    """
    A single class to handle all CRUD operations for Category.
    - GET: Retrieve all categories or a single category by ID.
    - POST: Create a new category.
    - PUT: Update an existing category (full update).
    - PATCH: Update an existing category (partial update).
    - DELETE: Delete a category by ID.
    """

    def get(self, request, pk=None):
        if pk:
            try:
                category = Category.objects.get(pk=pk)
                serializer = CategorySerializerK(category)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Category.DoesNotExist:
                return Response({'error': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            categories = Category.objects.all()
            serializer = CategorySerializerK(categories, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CategorySerializerK(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({'error': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CategorySerializerK(category, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({'error': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CategorySerializerK(
            category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({'error': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)

        category.delete()
        return Response({'message': 'Category deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)


class ModuleAPIView(APIView):
    """
    A single class to handle all CRUD operations for Module.
    - GET: Retrieve all modules or a single module by ID.
    - POST: Create a new module.
    - PUT: Update an existing module (full update).
    - PATCH: Update an existing module (partial update).
    - DELETE: Delete a module by ID.
    """

    def get(self, request, pk=None):
        if pk:
            try:
                module = Module.objects.get(pk=pk)
                serializer = ModuleSerializer(module)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Module.DoesNotExist:
                return Response({'error': 'Module not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            modules = Module.objects.all()
            serializer = ModuleSerializer(modules, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ModuleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            module = Module.objects.get(pk=pk)
        except Module.DoesNotExist:
            return Response({'error': 'Module not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ModuleSerializer(module, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        try:
            module = Module.objects.get(pk=pk)
        except Module.DoesNotExist:
            return Response({'error': 'Module not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ModuleSerializer(module, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            module = Module.objects.get(pk=pk)
        except Module.DoesNotExist:
            return Response({'error': 'Module not found.'}, status=status.HTTP_404_NOT_FOUND)

        module.delete()
        return Response({'message': 'Module deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)


class TeamAPIView(APIView):
    """
    A single class to handle all CRUD operations for Module.
    - GET: Retrieve all modules or a single module by ID.
    - POST: Create a new module.
    - PUT: Update an existing module (full update).
    - PATCH: Update an existing module (partial update).
    - DELETE: Delete a module by ID.
    """

    def get(self, request, pk=None):
        if pk:
            try:
                module = Team.objects.get(pk=pk)
                serializer = TeamSerializer(module)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Module.DoesNotExist:
                return Response({'error': 'Module not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            modules = Team.objects.all()
            serializer = TeamSerializer(modules, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TeamSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            module = Team.objects.get(pk=pk)
        except Module.DoesNotExist:
            return Response({'error': 'Module not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = TeamSerializer(module, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        try:
            module = Team.objects.get(pk=pk)
        except Module.DoesNotExist:
            return Response({'error': 'Module not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = TeamSerializer(module, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            module = Team.objects.get(pk=pk)
        except Module.DoesNotExist:
            return Response({'error': 'Module not found.'}, status=status.HTTP_404_NOT_FOUND)

        module.delete()
        return Response({'message': 'Module deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)


class TicketAPIView(APIView):
    """
    A single class to handle all CRUD operations for Ticket.
    - GET: Retrieve all tickets or a single ticket by ID.
    - POST: Create a new ticket.
    - PUT: Update an existing ticket (full update).
    - PATCH: Update an existing ticket (partial update).
    - DELETE: Delete a ticket by ID.
    """

    def get(self, request, pk=None):
        if pk:
            try:
                ticket = Ticket.objects.get(pk=pk)
                serializer = TicketSerializer(ticket)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Ticket.DoesNotExist:
                return Response({'error': 'Ticket not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            tickets = Ticket.objects.all()
            serializer = TicketSerializer(tickets, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data

        try:
            module = get_object_or_404(Module, pk=data.get('module'))
            project = get_object_or_404(Project, pk=data.get('project'))
            category = get_object_or_404(Category, pk=data.get('category'))

            # Create the ticket
            serializer = TicketSerializer(data=data)
            if serializer.is_valid():
                serializer.save(user=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            return Response({
                "message": "Invalid data provided.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Module.DoesNotExist:
            return Response({
                "message": "Invalid module ID.",
                "error": f"Module with ID {data.get('module')} does not exist."
            }, status=status.HTTP_400_BAD_REQUEST)

        except Project.DoesNotExist:
            return Response({
                "message": "Invalid project ID.",
                "error": f"Project with ID {data.get('project')} does not exist."
            }, status=status.HTTP_400_BAD_REQUEST)

        except Category.DoesNotExist:
            return Response({
                "message": "Invalid category ID.",
                "error": f"Category with ID {data.get('category')} does not exist."
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "message": "An unexpected error occurred while creating the ticket.",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, pk):
        try:
            ticket = Ticket.objects.get(pk=pk)
        except Ticket.DoesNotExist:
            return Response({'error': 'Ticket not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = TicketSerializer(ticket, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        try:
            ticket = Ticket.objects.get(pk=pk)
        except Ticket.DoesNotExist:
            return Response({'error': 'Ticket not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = TicketSerializer(ticket, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            ticket = Ticket.objects.get(pk=pk)
        except Ticket.DoesNotExist:
            return Response({'error': 'Ticket not found.'}, status=status.HTTP_404_NOT_FOUND)

        ticket.delete()
        return Response({'message': 'Ticket deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)


class TicketAssignmentViewSet(ModelViewSet):
    """
    ViewSet for handling all CRUD operations for TicketAssignment.
    """
    queryset = TicketAssignment.objects.all()
    serializer_class = TicketAssignmentSerializer
    # permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Override the create method to validate relationships.
        """
        data = request.data
        ticket = get_object_or_404(Ticket, pk=data.get('ticket'))
        assigned_to = get_object_or_404(Team, pk=data.get('assigned_to'))

        # Check if an assignment already exists for this ticket and team with the same status
        if TicketAssignment.objects.filter(
                ticket=ticket, assigned_to=assigned_to, status=data.get('status')).exists():
            return Response(
                {"error": "An assignment with this ticket, team, and status already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        """
        Optionally filter assignments by ticket ID or status.
        """
        queryset = super().get_queryset()
        ticket_id = self.request.query_params.get('ticket_id')
        status_filter = self.request.query_params.get('status')

        if ticket_id:
            queryset = queryset.filter(ticket__ticket_id=ticket_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset


class TicketKAPIView(APIView):
    """
    API to retrieve all tickets or a specific ticket with its assignments.
    """

    def get_ticket_data(self, ticket):
        """
        Helper function to construct ticket details with its assignments.
        """
        try:
            # Fetch related ticket assignments
            assignments = TicketAssignment.objects.filter(ticket=ticket)
            assignment_data = [
                {
                    "ticket_assignment_id": assignment.ticket_assignment_id,
                    "assigned_to": assignment.assigned_to.team_id,
                    "assigned_to_name": assignment.assigned_to.name,
                    "status": assignment.status,
                    "comments": assignment.comments,
                    "assigned_at": assignment.assigned_at
                }
                for assignment in assignments
            ]
        except TicketAssignment.DoesNotExist:
            assignment_data = []

        # Construct ticket data
        return {
            "ticket_id": ticket.ticket_id,
            "title": ticket.title,
            "description": ticket.description,
            "priority": ticket.priority,
            "project_type": ticket.project_type,
            "status": ticket.status,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
            "user": ticket.user.id if ticket.user else None,
            "user_name": ticket.user.name if ticket.user else None,
            "module": ticket.module.id if ticket.module else None,
            "module_name": ticket.module.name if ticket.module else None,
            "project": ticket.project.id if ticket.project else None,
            "category": ticket.category.category_id if ticket.category else None,
            "category_name": ticket.category.name if ticket.category else None,
            "ticket_assignments": assignment_data,
        }

    def get(self, request, pk=None):
        if pk is None:
            tickets = Ticket.objects.select_related(
                'module', 'category', 'project', 'user'
            ).all()
            tickets_data = [self.get_ticket_data(ticket) for ticket in tickets]
            return JsonResponse({
                "success": True,
                "data": tickets_data
            }, status=200)
        else:
            try:
                ticket = get_object_or_404(
                    Ticket.objects.select_related(
                        'module', 'category', 'project', 'user'),
                    ticket_id=pk
                )
                ticket_data = self.get_ticket_data(ticket)
                return JsonResponse({
                    "success": True,
                    "data": ticket_data
                }, status=200)
            except Exception as e:
                return JsonResponse({
                    "success": False,
                    "message": str(e)
                }, status=500)


class TicketPatchAPIView(APIView):

    def patch(self, request, pk):
        try:
            ticket = get_object_or_404(Ticket, ticket_id=pk)
            allowed_fields = [
                'title', 'description', 'priority', 'project_type',
                'status', 'module', 'project', 'category'
            ]

            data = request.data
            status_changed = False
            old_status = ticket.status

            assigned_to = data.get('assigned_to', None)
            for field, value in data.items():
                if field in allowed_fields:
                    if field in ['module', 'project', 'category']:
                        related_model = getattr(
                            Ticket._meta.get_field(field), 'related_model', None)
                        if related_model:
                            try:
                                value = related_model.objects.get(pk=value)
                            except related_model.DoesNotExist:
                                return JsonResponse({
                                    "success": False,
                                    "message": f"Invalid {field} ID: {value}"
                                }, status=400)

                    if field == 'status' and value != ticket.status:
                        status_changed = True
                    setattr(ticket, field, value)

            ticket.full_clean()
            ticket.save()

            if status_changed:
                if not assigned_to:
                    latest_assignment = TicketAssignment.objects.filter(
                        ticket=ticket).order_by('-assigned_at').first()
                    assigned_to = latest_assignment.assigned_to if latest_assignment else None

                if assigned_to:
                    if not Team.objects.filter(pk=assigned_to).exists():
                        return JsonResponse({
                            "success": False,
                            "message": f"Invalid assigned_to ID: {assigned_to}"
                        }, status=400)

                TicketAssignment.objects.create(
                    ticket=ticket,
                    assigned_to=Team.objects.get(
                        pk=assigned_to) if assigned_to else None,
                    status=ticket.status,
                    comments=f"Status changed from '{old_status}' to '{ticket.status}'",
                    assigned_at=datetime.now()
                )

            return JsonResponse({
                "success": True,
                "message": "Ticket updated successfully.",
                "data": {
                    "ticket_id": ticket.ticket_id,
                    "title": ticket.title,
                    "description": ticket.description,
                    "priority": ticket.get_priority_display(),
                    "project_type": ticket.get_project_type_display(),
                    "status": ticket.get_status_display(),
                    "module": ticket.module.id if ticket.module else None,
                    "project": ticket.project.id if ticket.project else None,
                    "category": ticket.category.category_id if ticket.category else None,
                    "updated_at": ticket.updated_at
                }
            }, status=200)

        except ValidationError as e:
            return JsonResponse({
                "success": False,
                "message": "Validation error.",
                "errors": e.message_dict
            }, status=400)
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": "An error occurred while updating the ticket.",
                "error": str(e)
            }, status=500)


class CustomerTicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

    def create(self, request):
        user_input = request.data.get("message")

        ticket_data = self.generate_ticket_details(user_input)

        ticket = Ticket.objects.create(
            user=5177,
            title=ticket_data['title'],
            description=ticket_data['description'],
            module=Module.objects.get(name=ticket_data['module']),
            project=100009,
            priority=ticket_data['priority'],
            category=Category.objects.get(name=ticket_data['category']),
            project_type=ticket_data['ticket_type'],
            status="Open",
            created_at=now()
        )

        return Response({"message": "Ticket created successfully", "ticket_id": ticket.ticket_id}, status=status.HTTP_201_CREATED)


class PromptAPIView(APIView):
    """
    API to handle GET and POST requests for prompts.
    """

    def get(self, request):
        """
        Retrieve prompts. Can filter by name.
        """
        name = request.query_params.get('name')
        if name:
            prompts = Prompt.objects.filter(name=name).order_by('-created_at')
        else:
            prompts = Prompt.objects.all().order_by('-created_at')

        serializer = PromptSerializer(prompts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Create a new prompt entry.
        """
        serializer = PromptSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResponsiveAgentView(APIView):
    def get(self, request, ticket_id, format=None):
        response_text = process_ticket_response(ticket_id)
        return Response({"response": response_text})


# ----------------------------------Azure------Openai--------------------------------------------


class AIResponseAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            user_message = data.get("user_message")
            chatwindow_id = data.get("chatwindow_id", 123456)
            project_id = request.data.get("project_id", 100009)
            user_id = data.get("user", 5177)

            try:
                user = User.objects.get(id=user_id)
            except ObjectDoesNotExist:
                return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
            try:
                project_instance = Project.objects.get(id=project_id)
            except ObjectDoesNotExist:
                return Response({"error": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

            if not user_message:
                return Response({"success": False, "error": "Missing required parameters."}, status=status.HTTP_400_BAD_REQUEST)
            memory_context = fetch_memory_contexts(
                chatwindow_id=int(chatwindow_id), user=user)
            response_data, answers = get_ai_responses(
                user_message=user_message, chatwindow_id=chatwindow_id, user=user)
            chat_entry = ChatConvo.objects.create(
                chatwindow_id=chatwindow_id, user=user, project_id=project_id, user_query=user_message, response=response_data, answer=answers)
            tic = response_data.get("ticket_preview")
            if tic:
                tic_details = response_data.get("ticket_details", [])
                tic_id = tic_details[0].get("ticket_id")

                res = postprocess_tickets(
                    user_id, response_data, project_id, tic_id)

            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ----------------solution agent --------------------------------------------------------


class TicketSolutionView(APIView):
    """
    API View to fetch ticket details including ticket ID, title, and solution.
    """

    def get(self, request, ticket_id):
        try:
            ticket = Ticket.objects.get(ticket_id=ticket_id)
        except Ticket.DoesNotExist:
            return Response({"error": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND)

        # Return ticket details
        return Response({
            "ticket_id": ticket.ticket_id,
            "title": ticket.title,
            "solution": ticket.solution
        }, status=status.HTTP_200_OK)


# ------------------------------------------------------------------


class SerialTrackingView(APIView):
    def post(self, request, *args, **kwargs):
        s3_url = request.data.get("s3_url")
        serial_number = request.data.get("serial_number")

        if not s3_url:
            return Response({"error": "S3 URL is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not serial_number:
            return Response({"error": "Serial number is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            file_stream = fetch_excel_from_s3(s3_url)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        file_stream.seek(0)
        if not serial_number_exists_in_excel(file_stream, serial_number):
            return Response({"error": "Serial number not found in the file"}, status=status.HTTP_404_NOT_FOUND)

        industry_agent_prompt = Prompt.objects.filter(
            name="Industry_agent").first()
        if not industry_agent_prompt:
            return Response({"error": "Prompt not found in database"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        api_url = settings.OPENAI_API_URL
        api_key = settings.OPENAI_API_KEY
        file_stream.seek(0)
        response = track_serial_number(
            file_stream, serial_number, api_url, api_key, industry_agent_prompt.content)

        return Response(response, status=status.HTTP_200_OK)


class pharmaS3FileView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request, *args, **kwargs):
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        response = s3_client.list_objects_v2(
            Bucket=settings.PHARMA_AWS_S3_BUCKET_NAME, Prefix=settings.AWS_FOLDER_PREFIX)

        files = []
        if "Contents" in response:
            for idx, obj in enumerate(response["Contents"], start=1):
                key = obj["Key"]
                if key.endswith("/"):
                    continue
                presigned_url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": settings.PHARMA_AWS_S3_BUCKET_NAME, "Key": key},
                    ExpiresIn=3600,
                )

                files.append({
                    "id": idx,
                    "filename": key.split("/")[-1],
                    "presigned_url": presigned_url
                })

        return Response(files, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        if "file" not in request.FILES:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES["file"]
        s3_key = settings.AWS_FOLDER_PREFIX + file.name

        try:
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            s3_client.upload_fileobj(
                file, settings.PHARMA_AWS_S3_BUCKET_NAME, s3_key)

            return Response({"message": "File uploaded successfully!", "filename": file.name}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResponseAgent(APIView):
    def get(self, request, ticket_id):
        try:
            try:
                Ticket_instance = Ticket.objects.get(ticket_id=ticket_id)
            except ObjectDoesNotExist:
                return Response({"error": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND)
            results = Response_Agent_function(ticket_id)
            return Response(results, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# -------------------Compliance Agent--------------------------------------------


class ComplianceView(APIView):
    def post(self, request, *args, **kwargs):
        # Get S3 URL from payload
        s3_url = request.data.get("s3_url")

        if not s3_url:
            return Response({"error": "S3 URL is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch Excel file from S3
        try:
            file_stream = validate_fetch_excel_from_s3(s3_url)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Retrieve compliance prompt from database
        compliance_prompt = Prompt.objects.filter(
            name="compliance_agent").first()
        if not compliance_prompt:
            return Response({"error": "Compliance prompt not found in database"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Extract data from Excel
        try:
            raw_text = validate_extract_text_from_excel(file_stream)
        except Exception as e:
            return Response({"error": f"Excel extraction failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Azure OpenAI API config
        api_url = settings.OPENAI_API_URL
        api_key = settings.OPENAI_API_KEY

        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }

        # Prepare the payload for OpenAI
        payload = {
            "messages": [
                {"role": "system", "content": compliance_prompt.content},
                {"role": "user", "content": json.dumps(raw_text, indent=2)}
            ],
            "temperature": 0.5
        }

        # Send request to Azure OpenAI
        try:
            response = requests.post(api_url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                ai_response = data.get("choices", [{}])[0].get(
                    "message", {}).get("content", "{}")

                # Clean AI response if wrapped in code blocks
                ai_response = re.sub(r"```json|```", "", ai_response).strip()

                return Response({
                    "success": True,
                    "response": ai_response
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "success": False,
                    "error": f"Error: {response.status_code}, {response.text}"
                }, status=response.status_code)
        except Exception as e:
            return Response({"error": f"OpenAI API Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def assign_ticket_api(request):
    """
    API to assign a ticket to the most suitable team.
    """
    ticket_id = request.data.get("ticket_id")

    # Validate ticket_id
    if not ticket_id:
        return Response({"success": False, "data": {"error": "ticket_id is required"}}, status=status.HTTP_400_BAD_REQUEST)

    try:
        api_url = settings.OPENAI_API_URL
        api_key = settings.OPENAI_API_KEY
        assigned_team = get_suitable_team(ticket_id, api_url, api_key)
        return Response({"success": True, "data": assigned_team}, status=status.HTTP_200_OK)

    except ValueError:
        return Response({"success": False, "data": {"error": "Invalid ticket_id, must be an integer"}}, status=status.HTTP_400_BAD_REQUEST)


class SLABreachNotificationAPIView(APIView):
    def get(self, request):
        try:
            send_sla_breach_notifications()
            process_ticket_assignments()
            return Response({"message": "Response Agent Activity..."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetUserChatHistoryAPIView(APIView):
    def get(self, request):
        user_id = request.GET.get("user_id")

        if not user_id:
            return Response({"success": False, "error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            chats = ChatConvo.objects.filter(
                user_id=user_id).order_by('timestamp')
            if not chats.exists():
                return Response({"success": False, "message": "No chats found for the given user"}, status=status.HTTP_404_NOT_FOUND)

            chat_data = defaultdict(list)
            for chat in chats:
                chat_data[chat.chatwindow_id].append({
                    "user_query": chat.user_query,
                    "response": chat.answer,
                    "timestamp": chat.timestamp
                })

            return Response({"success": True, "data": chat_data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetProActiveIssues(APIView):
    """
    API View to fetch and clean XML data from SAP OData service with optional parameters.
    """

    def get(self, request):
        try:
            bukrs = request.GET.get("Bukrs", "1810")
            sap_client = request.GET.get("sap-client", "200")
            url = f"https://server1.n-labs.ai:44300/sap/opu/odata/sap/ZPOSTING_PERIOD_SRV/GetPeriodSet(Bukrs='{bukrs}')?sap-client={sap_client}&$format=json"

            username = os.getenv("SAP_USERNAME", "NAPP_USER")
            password = os.getenv("SAP_PASSWORD", "Nivedauser1")

            cleaned_json_response = fetch_cleaned_json(url, username, password)
            message = cleaned_json_response.get(
                "d", {}).get("Message", "No message found")
            if "error" in cleaned_json_response:
                return Response(cleaned_json_response, status=status.HTTP_400_BAD_REQUEST)

            return Response(message, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
