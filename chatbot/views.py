import json

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .gemini_service import GeminiError, ask_gemini
from .models import ChatMessage, ChatSession

HISTORY_LIMIT = 12  # past turns sent back to Gemini for context
SIDEBAR_HISTORY_LIMIT = 15  # past conversations shown in the sidebar


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("chatbot:index")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("chatbot:index")
    else:
        form = UserCreationForm()

    return render(request, "chatbot/auth.html", {"form": form, "mode": "signup"})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("chatbot:index")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("chatbot:index")
    else:
        form = AuthenticationForm()

    return render(request, "chatbot/auth.html", {"form": form, "mode": "login"})


@login_required
def logout_view(request):
    logout(request)
    return redirect("chatbot:login")


@login_required
def index(request, session_id=None):
    sessions = ChatSession.objects.filter(user=request.user)[:SIDEBAR_HISTORY_LIMIT]

    if session_id:
        active_session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    else:
        active_session = sessions.first()

    messages = active_session.messages.all() if active_session else []

    return render(request, "chatbot/index.html", {
        "sessions": sessions,
        "active_session": active_session,
        "messages": messages,
    })


@login_required
@require_POST
def new_session(request):
    session = ChatSession.objects.create(user=request.user)
    return JsonResponse({"session_id": session.id})


@csrf_exempt
@login_required
@require_POST
def send_message(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request body."}, status=400)

    user_text = (payload.get("message") or "").strip()
    session_id = payload.get("session_id")

    if not user_text:
        return JsonResponse({"error": "Please describe your symptoms first."}, status=400)
    if len(user_text) > 2000:
        return JsonResponse({"error": "Message is too long."}, status=400)

    if session_id:
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    else:
        session = ChatSession.objects.create(user=request.user)

    past_turns = list(session.messages.order_by("-created_at")[:HISTORY_LIMIT])[::-1]
    history = [{"role": m.role, "content": m.content} for m in past_turns]

    ChatMessage.objects.create(session=session, role="user", content=user_text)

    try:
        reply_text = ask_gemini(user_text, history)
    except GeminiError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    ChatMessage.objects.create(session=session, role="bot", content=reply_text)

    return JsonResponse({
        "reply": reply_text,
        "session_id": session.id,
        "session_title": session.title,
    })


@login_required
@require_POST
def delete_session(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    session.delete()
    return JsonResponse({"status": "ok"})
