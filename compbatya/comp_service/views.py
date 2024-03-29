from django.core.cache import cache
from django.db.models import Q
from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from .models import Services, Specialists, Requests, Owners
from .serializers import *
from .permissions import IsAdmin
from .tasks import send_mail_to_managers



class SmallResultSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    


class ServicesAPIList(generics.ListAPIView):
    """View the all services"""

    serializer_class = ServicesSerializer
    pagination_class = SmallResultSetPagination


    def get_queryset(self):
        profile = self.kwargs.get('profile')
        if profile:
            result = cache.get(f'services_{profile}')
            if not result:
                result = Services.objects.filter(profile=profile)
                cache.set(f'services_{profile}', result, 60 * 60)
            return result
        
        result = cache.get('services')
        if not result:
            result = Services.objects.all()
            cache.set('services', result, 60 * 60)

        return result
    


class SpecialistsAPIList(generics.ListAPIView):
    """View the all specialists"""

    serializer_class = SpecialistsSerializer
    pagination_class = SmallResultSetPagination


    def get_queryset(self):
        profile = self.kwargs.get('profile')
        if profile:
            result = cache.get(f'specialists_{profile}')
            if not result:
                result = Specialists.objects.filter(profile__contains=Specialists.PROFILE_CHOICES[profile])
                cache.set(f'specialists_{profile}', result, 60 * 60 * 24)
            return result

        result = cache.get('specialists')
        if not result:
            result = Specialists.objects.all()
            cache.set('specialists', result, 60 * 60)

        return result

    

class CreateClient(generics.CreateAPIView):
    """Create the new client"""

    serializer_class = ClientsSerializer


    def post(self, request):
        phone = request.data['phone_number']
        name = request.data['name']
        try:
            client_mail = request.data['email']
        except KeyError:
            client_mail = None

        serializer = ClientsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
        else:
            client = Owners.objects.get(
                Q(phone_number=phone) | (Q(email=client_mail) & Q(email__isnull=False))
            )
            if client:
                client.requests.create()
            else:
                return Response(
                    data={'msg': 'Bad request'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        send_mail_to_managers.delay(phone, name, client_mail)

        response = Response(
            data={
                'msg': 'client successfully created',
                'client': serializer.data
            },
            status=status.HTTP_201_CREATED
        )
        return response

    

class RequestsViewSet(viewsets.ModelViewSet):
    """The viewset for viewing, creating, editing and deleting requests"""

    serializer_class = RequestsSerializer
    queryset = Requests.objects.all()


    @action(detail=False, methods=['get'],
            pagination_class = SmallResultSetPagination,
            permission_classes=[IsAdmin])
    def get_requests(self, request):
        queryset = Requests.objects.all()
        serializer = RequestsSerializer(queryset, many=True)
        return Response(serializer.data)
    

    def create(self, request):
        serializer = RequestsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response = Response(
            data={
                'msg': 'request successfully created',
                'request': serializer.data
            },
            status=status.HTTP_201_CREATED
        )
        return response
    

    @action(detail=True, methods=['patch'], permission_classes=[IsAdmin])
    def edit_request(self, request, *args, **kwargs):
        pk = kwargs.get('pk', None)
        if not pk:
            return Response(
                data={"error": "Method PATCH is not allowed"},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

        try:
            instance = Requests.objects.get(pk=pk)
        except:
            return Response(
                data={"error": "Object does not exists"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = RequestsSerializer(data=request.data,
                                        instance=instance,
                                        partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'msg': 'Request successfully updated',
            'request': serializer.data
        })
    

    @action(detail=True, methods=['delete'], permission_classes=[IsAdmin])
    def delete_request(self, request, *args, **kwargs):
        pk = kwargs.get('pk', None)
        if not pk:
            return Response(
                data={"error": "Method DELETE is not allowed"},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        try:
            instance = Requests.objects.get(pk=pk)
        except:
            return Response(
                data={"error": "Object does not exists"},
                status=status.HTTP_404_NOT_FOUND
            )

        instance.delete()
        return Response({'msg': f'Successfully delete request with pk={pk}'})
    


class DevicesViewSet(viewsets.ModelViewSet):
    """The viewset for viewing, createing and editing devices"""

    serializer_class = DevicesSerializer
    queryset = Devices.objects.all()
    permission_classes = (IsAdmin,)


    @action(detail=False, methods=['get'], pagination_class=SmallResultSetPagination)
    def get_devices_list(self, request):
        queryset = Devices.objects.all()
        serializer = DevicesSerializer(queryset, many=True)
        return Response(serializer.data)


    def create(self, request):
        serializer = DevicesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response = Response(
            data={
                'msg': 'device successfully created',
                'device': serializer.data
            },
            status=status.HTTP_201_CREATED
        )
        return response


    def partial_update(self, request, *args, **kwargs):
        pk = kwargs.get('pk', None)
        if not pk:
            return Response(
                data={'error': 'Method PATCH is not allowed'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        try:
            instance = Devices.objects.get(pk=pk)
        except:
            return Response(
                data={"error": "Object does not exists"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = DevicesSerializer(data=request.data,
                                       instance=instance,
                                       partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'msg': 'device successfully updated',
            'device': serializer.data
        })