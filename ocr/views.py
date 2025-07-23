from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.conf import settings
from django.views.decorators.http import require_http_methods
import os
import base64
import requests
import logging

from .models import Docs, UsersToDocs, Price, Cart
from django.contrib import messages
from django.db.models import Sum
from django.http import JsonResponse, HttpResponseForbidden

FASTAPI_URL_upload_doc = "http://fastweb:8000/api/v1/upload_doc"
FASTAPI_URL_doc_delete = "http://fastweb:8000/api/v1/doc_delete/{document_id}"
FASTAPI_URL_doc_analyse = "http://fastweb:8000/api/v1/doc_analyse/{document_id}"
FASTAPI_URL_get_text = "http://fastweb:8000/api/v1/get_text/{document_id}"

# Create your views here.

@login_required
@require_http_methods(["POST"])
def delete_image(request, doc_id):
    """
    Удаляет изображение, отправляя запрос в FastAPI, а затем удаляя локальные данные.
    """
    # Получаем документ или возвращаем 404 если не найден
    doc = get_object_or_404(Docs, id=doc_id)
    
    # Проверяем, что документ принадлежит текущему пользователю
    if not UsersToDocs.objects.filter(username=request.user.username, docs=doc).exists():
        return HttpResponseForbidden("У вас нет прав на удаление этого файла")
    
    try:
        # 1. Отправляем запрос на удаление в FastAPI
        delete_url = FASTAPI_URL_doc_delete.format(document_id=doc_id)
        response = requests.delete(
            delete_url,
            timeout=10  # 10 секунд таймаут на запрос
        )
        
        # Проверяем успешность ответа от FastAPI
        response.raise_for_status()
        
        # 2. Если FastAPI успешно обработал запрос, удаляем локальные данные
        try:
            # Удаляем файл с диска
            file_path = os.path.join(settings.MEDIA_ROOT, str(doc.file_path).replace(settings.MEDIA_URL, ''))
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Удаляем записи из базы данных
            UsersToDocs.objects.filter(docs=doc).delete()
            Cart.objects.filter(docs=doc).delete()
            doc.delete()
            
            messages.success(request, 'Файл успешно удален')
            
        except Exception as e:
            # Если не удалось удалить локально, логируем ошибку
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при удалении локальных данных документа {doc_id}: {str(e)}")
            messages.error(request, 'Файл удален из системы анализа, но возникла ошибка при удалении локальных данных')
    
    except requests.exceptions.RequestException as e:
        # Обработка ошибок при запросе к FastAPI
        error_message = f'Ошибка при удалении файла в системе анализа: {str(e)}'
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json().get('detail', 'Неизвестная ошибка')
                error_message = f'Ошибка от сервера анализа: {error_detail}'
            except:
                error_message = f'Ошибка сервера анализа: {e.response.status_code} {e.response.reason}'
        
        messages.error(request, error_message)
        return redirect('index')
    except Exception as e:
        # Обработка прочих ошибок
        messages.error(request, f'Непредвиденная ошибка при удалении файла: {str(e)}')
        return redirect('index')
    
    return redirect('index')

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
            resp = requests.post(FASTAPI_URL_upload_doc, data={
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
    doc = get_object_or_404(Docs, id=doc_id)
    
    # Проверяем, что документ принадлежит текущему пользователю
    if not UsersToDocs.objects.filter(username=request.user.username, docs=doc).exists():
        return HttpResponseForbidden("У вас нет прав на анализ этого файла")
    
    file_ext = os.path.splitext(doc.file_path)[1].replace('.', '').lower()
    price_obj = Price.objects.filter(file_type=file_ext).first()
    price_per_kb = price_obj.price if price_obj else 0
    order_price = doc.size * price_per_kb
    
    if request.method == 'POST':
        try:
            # Создаем запись о заказе
            cart = Cart.objects.create(
                user=request.user, 
                docs=doc, 
                order_price=order_price, 
                payment=False
            )
            
            # Отправляем запрос на анализ в FastAPI
            analyze_url = FASTAPI_URL_doc_analyse.format(document_id=doc_id)
            response = requests.post(
                analyze_url,
                timeout=30,  # 30 секунд на анализ
                json={
                    "document_id": doc_id,
                    "file_type": file_ext,
                    "size_kb": doc.size
                }
            )
            response.raise_for_status()
            
            return redirect('pay_order', cart_id=cart.id)
            
        except requests.exceptions.RequestException as e:
            # Если не удалось отправить на анализ, удаляем корзину
            if 'cart' in locals():
                cart.delete()
                
            error_message = f'Ошибка при отправке на анализ: {str(e)}'
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json().get('detail', 'Неизвестная ошибка')
                    error_message = f'Ошибка от сервера анализа: {error_detail}'
                except:
                    error_message = f'Ошибка сервера анализа: {e.response.status_code} {e.response.reason}'
            
            return render(request, 'ocr/order_analysis.html', {
                'doc': doc,
                'order_price': order_price,
                'price_per_kb': price_per_kb,
                'file_ext': file_ext,
                'error': error_message
            })
    
    return render(request, 'ocr/order_analysis.html', {
        'doc': doc,
        'order_price': order_price,
        'price_per_kb': price_per_kb,
        'file_ext': file_ext,
        'error': None
    })

@login_required
def pay_order(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id, user=request.user)
    
    if request.method == 'POST':
        try:
            # Помечаем заказ как оплаченный
            cart.payment = True
            cart.save()
            
            # Получаем результаты анализа из FastAPI
            result_url = FASTAPI_URL_get_text.format(document_id=cart.docs.id)
            response = requests.get(
                result_url,
                timeout=10  # 10 секунд на получение результатов
            )
            response.raise_for_status()
            
            # Сохраняем результаты анализа (если нужно)
            analysis_result = response.json()
            # cart.analysis_result = analysis_result  # Раскомментировать, если нужно сохранить
            # cart.save()
            
            return redirect('analysis_result', cart_id=cart.id)
            
        except requests.exceptions.RequestException as e:
            error_message = f'Ошибка при получении результатов анализа: {str(e)}'
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json().get('detail', 'Неизвестная ошибка')
                    error_message = f'Ошибка от сервера анализа: {error_detail}'
                except:
                    error_message = f'Ошибка сервера анализа: {e.response.status_code} {e.response.reason}'
            
            return render(request, 'ocr/pay_order.html', {
                'cart': cart,
                'error': error_message
            })
    
    return render(request, 'ocr/pay_order.html', {
        'cart': cart,
        'error': None
    })

@login_required
def analysis_result(request, cart_id):
    cart = get_object_or_404(Cart, id=cart_id, user=request.user)
    
    if not cart.payment:
        messages.error(request, 'Заказ не оплачен')
        return redirect('pay_order', cart_id=cart.id)
    
    analysis_result = None
    error = None
    
    try:
        # Получаем актуальные результаты анализа из FastAPI
        result_url = FASTAPI_URL_get_text.format(document_id=cart.docs.id)
        response = requests.get(
            result_url,
            timeout=10  # 10 секунд на получение результатов
        )
        response.raise_for_status()
        analysis_result = response.json()
        
    except requests.exceptions.RequestException as e:
        error = f'Ошибка при получении результатов анализа: {str(e)}'
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json().get('detail', 'Неизвестная ошибка')
                error = f'Ошибка от сервера анализа: {error_detail}'
            except:
                error = f'Ошибка сервера анализа: {e.response.status_code} {e.response.reason}'
    except Exception as e:
        error = f'Непредвиденная ошибка: {str(e)}'
    
    return render(request, 'ocr/analysis_result.html', {
        'cart': cart,
        'analysis_result': analysis_result,
        'error': error
    })
