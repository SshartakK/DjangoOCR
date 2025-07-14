from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.conf import settings
import os
import base64
import requests

from .models import Docs, UsersToDocs, Price, Cart

FASTAPI_URL = "http://127.0.0.1:8001/api/v1/upload_doc"

# Create your views here.

@login_required
def index(request):
    if request.user.is_superuser:
        docs = Docs.objects.all()
    else:
        user_docs_ids = UsersToDocs.objects.filter(username=request.user.username).values_list('docs_id', flat=True)
        docs = Docs.objects.filter(id__in=user_docs_ids)
    return render(request, 'ocr/index.html', {'docs': docs})

def login_view(request):
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            error = 'Неверные имя пользователя или пароль.'
    return render(request, 'ocr/login.html', {'error': error})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def add_image(request):
    error = None
    if request.method == 'POST' and request.FILES.get('image'):
        image = request.FILES['image']
        path = default_storage.save(f"uploads/{image.name}", image)
        file_path = os.path.join(settings.MEDIA_URL, path)
        size_kb = image.size / 1024
        doc = Docs.objects.create(file_path=file_path, size=size_kb)
        UsersToDocs.objects.create(username=request.user.username, docs=doc)
        # Отправка файла на FastAPI
        abs_file_path = os.path.join(settings.MEDIA_ROOT, path)
        with open(abs_file_path, "rb") as f:
            file_content = base64.b64encode(f.read()).decode()
        try:
            resp = requests.post(FASTAPI_URL, data={
                "file_name": os.path.basename(abs_file_path),
                "file_content": file_content
            })
            resp.raise_for_status()
        except Exception as e:
            error = f'Ошибка отправки на FastAPI: {e}'
        if not error:
            return redirect('index')
    return render(request, 'ocr/add_image.html', {'error': error})

@login_required
def order_analysis(request, doc_id):
    doc = Docs.objects.get(id=doc_id)
    file_ext = os.path.splitext(doc.file_path)[1].replace('.', '').lower()
    price_obj = Price.objects.filter(file_type=file_ext).first()
    price_per_kb = price_obj.price if price_obj else 0
    order_price = doc.size * price_per_kb
    if request.method == 'POST':
        Cart.objects.create(user=request.user, docs=doc, order_price=order_price, payment=False)
        return redirect('index')
    return render(request, 'ocr/order_analysis.html', {
        'doc': doc,
        'order_price': order_price,
        'price_per_kb': price_per_kb,
        'file_ext': file_ext,
        'error': None
    })

@login_required
def pay_order(request, cart_id):
    cart = Cart.objects.get(id=cart_id, user=request.user)
    if request.method == 'POST':
        cart.payment = True
        cart.save()
        # Здесь в будущем можно отправить сигнал для анализа через FastAPI
        return redirect('analysis_result', cart_id=cart.id)
    return render(request, 'ocr/pay_order.html', {'cart': cart})

@login_required
def analysis_result(request, cart_id):
    cart = Cart.objects.get(id=cart_id, user=request.user)
    # Здесь в будущем выводить результат анализа, пока просто подтверждение оплаты и заказа
    return render(request, 'ocr/analysis_result.html', {'cart': cart})
