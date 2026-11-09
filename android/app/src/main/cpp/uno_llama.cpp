// UNO experimental CPU-only GGUF inference. No Android permissions, actions or model training.
// API pinned to ggml-org/llama.cpp a4d4f2fd4ec85ec6a0a9ece4870416c1b6cc24f5 (MIT).
#include <jni.h>
#include "llama.h"
#include <atomic>
#include <algorithm>
#include <mutex>
#include <string>
#include <vector>
#include <memory>

namespace {
std::mutex model_mutex;
std::atomic<bool> cancel_generation{false};
llama_model * model = nullptr;
bool backend_initialized = false;

void failure(JNIEnv * env, const char * why) {
    jclass cls = env->FindClass("java/lang/IllegalStateException");
    if (cls) env->ThrowNew(cls, why);
}
struct NativeString {
    JNIEnv * env; jstring j; const char * p;
    NativeString(JNIEnv * e, jstring s) : env(e), j(s), p(s ? e->GetStringUTFChars(s, nullptr) : nullptr) {}
    ~NativeString() { if (p) env->ReleaseStringUTFChars(j, p); }
};
void fill(llama_batch_ext * batch, const std::vector<llama_token> & ids, int start, int count, bool logits) {
    llama_batch_ext_clear(batch);
    for (int i = 0; i < count; ++i) {
        const int idx = llama_batch_ext_add_token(batch, 0, ids[start + i]);
        if (idx < 0) return;
        const llama_pos pos = start + i;
        llama_batch_ext_set_pos(batch, idx, &pos);
    }
    if (logits) llama_batch_ext_set_output_logits(batch, count - 1, true);
}
jbyteArray bytes(JNIEnv * env, const std::string & text) {
    jbyteArray result = env->NewByteArray(static_cast<jsize>(text.size()));
    if (result && !text.empty()) env->SetByteArrayRegion(result, 0, static_cast<jsize>(text.size()),
                                                           reinterpret_cast<const jbyte *>(text.data()));
    return result;
}
}

extern "C" JNIEXPORT jboolean JNICALL
Java_org_unovyra_uno_UnoNativeEngine_load(JNIEnv * env, jobject, jstring path) {
    std::lock_guard<std::mutex> guard(model_mutex);
    NativeString file(env, path);
    if (!file.p || !file.p[0]) { failure(env, "MODEL_PATH_EMPTY"); return JNI_FALSE; }
    if (!backend_initialized) { llama_backend_init(); backend_initialized = true; }
    if (model) { llama_model_free(model); model = nullptr; }
    auto params = llama_model_default_params();
    params.n_gpu_layers = 0; // Safest first A52/Huawei measurement: CPU-only.
    model = llama_model_load_from_file(file.p, params);
    if (!model) { failure(env, "GGUF_LOAD_FAILED"); return JNI_FALSE; }
    return JNI_TRUE;
}

extern "C" JNIEXPORT void JNICALL
Java_org_unovyra_uno_UnoNativeEngine_cancel(JNIEnv *, jobject) {
    cancel_generation.store(true, std::memory_order_release);
}

extern "C" JNIEXPORT void JNICALL
Java_org_unovyra_uno_UnoNativeEngine_resetCancel(JNIEnv *, jobject) {
    cancel_generation.store(false, std::memory_order_release);
}

extern "C" JNIEXPORT void JNICALL
Java_org_unovyra_uno_UnoNativeEngine_unload(JNIEnv *, jobject) {
    cancel_generation.store(true, std::memory_order_release);
    std::lock_guard<std::mutex> guard(model_mutex);
    if (model) { llama_model_free(model); model = nullptr; }
}

extern "C" JNIEXPORT jbyteArray JNICALL
Java_org_unovyra_uno_UnoNativeEngine_generate(
    JNIEnv * env, jobject, jobjectArray jroles, jobjectArray jcontents, jint max_tokens, jobject receiver) {
    std::lock_guard<std::mutex> guard(model_mutex);
    if (!model || !receiver || !jroles || !jcontents || max_tokens < 1 || max_tokens > 256) {
        failure(env, "MODEL_OR_GENERATION_ARGUMENTS_INVALID"); return nullptr;
    }
    const jsize count = env->GetArrayLength(jroles);
    if (count < 1 || count > 12 || count != env->GetArrayLength(jcontents)) {
        failure(env, "CHAT_HISTORY_OUT_OF_RANGE"); return nullptr;
    }
    std::vector<std::string> roles, contents;
    roles.reserve(count); contents.reserve(count);
    for (jsize i = 0; i < count; ++i) {
        jstring role = static_cast<jstring>(env->GetObjectArrayElement(jroles, i));
        jstring content = static_cast<jstring>(env->GetObjectArrayElement(jcontents, i));
        {
            NativeString r(env, role), c(env, content);
            if (!r.p || !c.p || (std::string(r.p) != "user" &&
                std::string(r.p) != "assistant" && std::string(r.p) != "system") ||
                std::string(c.p).size() > 4096) {
                env->DeleteLocalRef(role); env->DeleteLocalRef(content);
                failure(env, "CHAT_ROLE_OR_CONTENT_REJECTED"); return nullptr;
            }
            roles.emplace_back(r.p); contents.emplace_back(c.p);
        }
        env->DeleteLocalRef(role); env->DeleteLocalRef(content);
    }
    std::vector<llama_chat_message> chat;
    chat.reserve(count);
    for (jsize i = 0; i < count; ++i) chat.push_back({roles[i].c_str(), contents[i].c_str()});
    const char * tmpl = llama_model_chat_template(model, nullptr);
    if (!tmpl) { failure(env, "MODEL_CHAT_TEMPLATE_MISSING"); return nullptr; }
    int32_t needed = llama_chat_apply_template(tmpl, chat.data(), chat.size(), true, nullptr, 0);
    if (needed <= 0 || needed > 32768) { failure(env, "CHAT_TEMPLATE_UNSUPPORTED_OR_TOO_LONG"); return nullptr; }
    std::string prompt(needed, '\0');
    int32_t written = llama_chat_apply_template(tmpl, chat.data(), chat.size(), true,
                                                 prompt.data(), static_cast<int32_t>(prompt.size()));
    if (written <= 0 || written > needed) { failure(env, "CHAT_TEMPLATE_FORMAT_FAILED"); return nullptr; }
    prompt.resize(written);

    const llama_vocab * vocab = llama_model_get_vocab(model);
    int32_t required = llama_tokenize(vocab, prompt.data(), static_cast<int32_t>(prompt.size()),
                                       nullptr, 0, true, true);
    if (required >= 0) { failure(env, "TOKEN_COUNT_NOT_REPORTED"); return nullptr; }
    const int32_t n_prompt = -required;
    // Bound prompt BEFORE allocating context; no silent truncation or hidden extra context.
    constexpr int kContext = 2048;
    if (n_prompt < 1 || n_prompt + max_tokens >= kContext) {
        failure(env, "CONTEXT_LIMIT_REACHED_START_NEW_CHAT"); return nullptr;
    }
    std::vector<llama_token> tokens(n_prompt);
    if (llama_tokenize(vocab, prompt.data(), static_cast<int32_t>(prompt.size()),
                       tokens.data(), n_prompt, true, true) != n_prompt) {
        failure(env, "TOKENIZATION_FAILED"); return nullptr;
    }
    auto cp = llama_context_default_params();
    cp.n_ctx = kContext; cp.n_batch = 256; cp.n_ubatch = 256;
    cp.n_threads = 4; cp.n_threads_batch = 4;
    std::unique_ptr<llama_context, decltype(&llama_free)> ctx(llama_init_from_model(model, cp), llama_free);
    if (!ctx) { failure(env, "CONTEXT_ALLOCATION_FAILED"); return nullptr; }
    std::unique_ptr<llama_batch_ext, decltype(&llama_batch_ext_free)> batch(llama_batch_ext_init(ctx.get()), llama_batch_ext_free);
    auto sp = llama_sampler_chain_default_params();
    std::unique_ptr<llama_sampler, decltype(&llama_sampler_free)> sampler(llama_sampler_chain_init(sp), llama_sampler_free);
    if (!batch || !sampler) { failure(env, "INFERENCE_ALLOCATION_FAILED"); return nullptr; }
    llama_sampler_chain_add(sampler.get(), llama_sampler_init_top_k(40));
    llama_sampler_chain_add(sampler.get(), llama_sampler_init_temp(0.7f));
    llama_sampler_chain_add(sampler.get(), llama_sampler_init_dist(LLAMA_DEFAULT_SEED));

    // Rebuild bounded prompt every turn; no uncontrolled native KV state across turns.
    for (int pos = 0; pos < n_prompt; pos += 256) {
        if (cancel_generation.load(std::memory_order_acquire)) return bytes(env, "");
        const int n = std::min(256, n_prompt - pos);
        fill(batch.get(), tokens, pos, n, pos + n == n_prompt);
        if (llama_process(ctx.get(), LLAMA_PROCESS_TYPE_DECODE, batch.get()) != 0) {
            failure(env, "PROMPT_DECODE_FAILED"); return nullptr;
        }
    }
    jclass callback_cls = env->GetObjectClass(receiver);
    jmethodID progress = callback_cls ? env->GetMethodID(callback_cls, "onTokens", "([B)V") : nullptr;
    if (!progress) { failure(env, "STREAM_CALLBACK_UNAVAILABLE"); return nullptr; }
    std::string answer;
    for (int i = 0; i < max_tokens && !cancel_generation.load(std::memory_order_acquire); ++i) {
        const llama_token token = llama_sampler_sample(sampler.get(), ctx.get(), -1);
        if (llama_vocab_is_eog(vocab, token)) break;
        char buf[256];
        const int piece_size = llama_token_to_piece(vocab, token, buf, sizeof(buf), 0, false);
        if (piece_size < 0 || piece_size > static_cast<int>(sizeof(buf))) {
            failure(env, "TOKEN_PIECE_CONVERSION_FAILED"); return nullptr;
        }
        answer.append(buf, piece_size);
        jbyteArray snapshot = bytes(env, answer);
        if (!snapshot) return nullptr;
        env->CallVoidMethod(receiver, progress, snapshot);
        env->DeleteLocalRef(snapshot);
        if (env->ExceptionCheck()) return nullptr;
        if (i + 1 >= max_tokens || cancel_generation.load(std::memory_order_acquire)) break;
        llama_batch_ext_clear(batch.get());
        const int idx = llama_batch_ext_add_token(batch.get(), 0, token);
        const llama_pos at = n_prompt + i;
        if (idx < 0 || !llama_batch_ext_set_pos(batch.get(), idx, &at) ||
            !llama_batch_ext_set_output_logits(batch.get(), idx, true) ||
            llama_process(ctx.get(), LLAMA_PROCESS_TYPE_DECODE, batch.get()) != 0) {
            failure(env, "TOKEN_DECODE_FAILED"); return nullptr;
        }
    }
    return bytes(env, answer);
}
