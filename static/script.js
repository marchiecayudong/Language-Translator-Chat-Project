// Auto scroll chat
window.onload = function() {
    var chatBox = document.getElementById("chatBox");
    if (chatBox) {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
};

// Show loading spinner
function showLoading(){
    var text = document.getElementById("textInput").value;
    if(text.trim() === "") return false;

    var typing = document.getElementById("typingIndicator");
    if (typing) {
        typing.innerHTML = '<div class="loader"></div> Translating...';
    }

    return true;
}

// Voice Input
function startVoice(){
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert("Voice recognition not supported in this browser.");
        return;
    }

    var recognition = new(window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = "en-US";
    recognition.start();

    recognition.onresult = function(event){
        document.getElementById("textInput").value =
            event.results[0][0].transcript;
    };
}

// Text-to-Speech
function speakText(text){
    var speech = new SpeechSynthesisUtterance(text);
    speech.rate = 1;
    speech.pitch = 1;
    speech.volume = 1;
    speechSynthesis.speak(speech);
}

// Register Service Worker
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js')
        .then(() => console.log("Service Worker Registered"));
}