import json
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse,Http404
from api.serializers import MyTokenObtainPairSerializer, RegisterSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from django.views.generic import TemplateView

User=get_user_model()

#project imports
from api.models import Game
from api.serializers  import GameSerializer
import sudokum


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

@api_view(['GET'])
def getRoutes(request):
    routes = [
        '/api/',
        '/api/token/',
        '/api/register/',
        '/api/token/refresh/',
        '/api/test/',
        '/api/docs/',
        '/api/teams/',
        '/api/projects/',
        '/api/profile/',
    ]
    # for urls in urlpatterns:
    #     routes.append(urls.pattern._route)

    return Response(routes)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def testEndPoint(request):
    if request.method == 'GET':
        data = f"Congratulation {request.user}, your API just responded to GET request"
        return Response({'response': data}, status=status.HTTP_200_OK)
    elif request.method == 'POST':
        try:
            body = request.body.decode('utf-8')
            data = json.loads(body)
            if 'text' not in data:
                return Response("Invalid JSON data", status.HTTP_400_BAD_REQUEST)
            text = data.get('text')
            data = f'Congratulation your API just responded to POST request with text: {text}'
            return Response({'response': data}, status=status.HTTP_200_OK)
        except json.JSONDecodeError:
            return Response("Invalid JSON data", status.HTTP_400_BAD_REQUEST)
    return Response("Invalid JSON data", status.HTTP_400_BAD_REQUEST)


class NewGameAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        user=self.request.user
        new_board=sudokum.generate(mask_rate=user.level/10)
        solved,new_board_solution=sudokum.solve(new_board)
        while not solved:
            new_board=sudokum.generate(mask_rate=user.level/10)
            solved,new_board_solution=sudokum.solve(new_board)
        game=Game.objects.create(
            user=user, 
            level=user.level,)
        game.playing_board=new_board
        game.playing_board_solution=new_board_solution
        game.save()
        return Response({"game_id":game.id},status=status.HTTP_201_CREATED)
    

class GameAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get_object(self, pk):
        try:
            return Game.objects.get(pk=pk)
        except Game.DoesNotExist:
            raise Http404
        
    def get(self, request, pk, format=None):
        game = self.get_object(pk)
        serializer = GameSerializer(game)
        if game.tries_left==0:
            return Response({"message":"Sorry you have no more tries left"},status=status.HTTP_200_OK)
        return Response(serializer.data)
    
    def post(self, request, pk, format=None):
        user=self.request.user
        game = self.get_object(pk)
        serializer = GameSerializer(game,data=request.data)
        if serializer.is_valid():
            user_submition=serializer.save()
            #wondering why this string here ->⬇ json submitted here is str too, so we need to convert it from int
            #to compare it with the solution  ⬇ 
            if user_submition.user_solution==str(game.playing_board_solution):
                return Response({"message":"Congratulation you solved the sudoku"},status=status.HTTP_200_OK)
            game.tries_left-=1
            game.save()    
            return Response({"message":"Sorry your solution is not correct"},status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)