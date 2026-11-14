# WP-06 / direct GGUF from Android SAF, no implicit 500 MB duplicate — 2026-11-09

Problem observed by owner: PocketPal and successive unique CI APK installations duplicate large model downloads. An app-private copy in WP-04 consumed additional hundreds of megabytes. This WP-06 does NOT delete existing files or model copies.

**Default new picker:** "GGUF без копии": selects an Android local DocumentsProvider URI (restricted to the existing three system authorities), opens a read-only `ParcelFileDescriptor`, and calls the existing native `UnoNativeEngine.load("/proc/self/fd/<n>")` synchronously while FD is held. It does not allocate a private GGUF file. It does NOT persist URI grants: after app/process restart owner must choose the shared file again. On unsupported fd / mmap / backend fail, it reports an error; never silently falls back to copying.

**Owner-option fallback:** "Резервный импорт GGUF с копированием" explicitly invokes preserved old hashed/private import code and commits the old model locator. No preexisting file is auto-deleted. Already-saved copies remain accessible to their installation package.

**Limits:** Android SELinux/proc-fd reopening, llama.cpp mmap and provider seekability are not proven for Samsung/Huawei until device trial. Some DocumentsProviders may satisfy EXTRA_LOCAL_ONLY while their underlying bytes use network; no strict offline proof until measured. Source model authenticity is not proved solely by provider authority. This is a UX/storage candidate, not a production security or neural model validation.

Android compilation + host tests required. ROOT AGENTS, main, old checkpoints and R5.3 retained unchanged. FOUNDATION_INCOMPLETE remains true.
