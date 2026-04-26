from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


BASE_URL = "https://api.elevenlabs.io"


class ApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, details: Any | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details

    @classmethod
    def from_response(cls, response: httpx.Response) -> "ApiError":
        try:
            payload = response.json()
        except ValueError:
            payload = response.text
        message = response.reason_phrase or "API request failed"
        if isinstance(payload, dict):
            detail = payload.get("detail")
            if isinstance(detail, dict):
                for key in ("message", "status", "code", "type"):
                    value = detail.get(key)
                    if isinstance(value, str) and value.strip():
                        message = value.strip()
                        break
                else:
                    message = "API request failed"
            elif isinstance(detail, str) and detail.strip():
                message = detail.strip()
            elif isinstance(payload.get("message"), str) and payload.get("message", "").strip():
                message = payload.get("message", "").strip()
            elif isinstance(payload.get("error"), str) and payload.get("error", "").strip():
                message = payload.get("error", "").strip()
            else:
                message = "API request failed"
        elif isinstance(payload, str) and payload.strip():
            message = payload.strip()
        return cls(message=message, status_code=response.status_code, details=payload)


@dataclass(slots=True)
class AudioPayload:
    audio: bytes
    content_type: str
    request_id: str
    character_count: str
    history_item_id: str


@dataclass(slots=True)
class BinaryPayload:
    content: bytes
    content_type: str


class ElevenLabsClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key.strip()
        self._client = httpx.Client(base_url=BASE_URL, timeout=90.0, follow_redirects=True)

    def set_api_key(self, api_key: str) -> None:
        self.api_key = api_key.strip()

    def close(self) -> None:
        self._client.close()

    def _headers(self, accept: str | None = "application/json") -> dict[str, str]:
        headers = {"xi-api-key": self.api_key}
        if accept:
            headers["Accept"] = accept
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: list[tuple[str, tuple[str, Any, str]]] | None = None,
        accept: str | None = "application/json",
    ) -> httpx.Response:
        response = self._client.request(
            method=method,
            url=path,
            headers=self._headers(accept=accept),
            params=params,
            json=json_body,
            data=data,
            files=files,
        )
        if response.is_error:
            raise ApiError.from_response(response)
        return response

    def get_user_subscription(self) -> dict[str, Any]:
        return self._request("GET", "/v1/user/subscription").json()

    def get_user(self) -> dict[str, Any]:
        return self._request("GET", "/v1/user").json()

    def get_models(self) -> list[dict[str, Any]]:
        return self._request("GET", "/v1/models").json()

    def get_voices(
        self,
        *,
        page_size: int = 100,
        search: str = "",
        category: str = "",
        next_page_token: str = "",
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page_size": page_size}
        if search:
            params["search"] = search
        if category:
            params["category"] = category
        if next_page_token:
            params["next_page_token"] = next_page_token
        return self._request("GET", "/v2/voices", params=params).json()

    def list_all_voices(self, *, search: str = "", category: str = "", max_pages: int = 12) -> list[dict[str, Any]]:
        voices: list[dict[str, Any]] = []
        next_page_token = ""
        pages = 0
        while pages < max_pages:
            payload = self.get_voices(
                page_size=100,
                search=search,
                category=category,
                next_page_token=next_page_token,
            )
            voices.extend(payload.get("voices", []))
            next_page_token = payload.get("next_page_token") or ""
            pages += 1
            if not payload.get("has_more") or not next_page_token:
                break
        return voices

    def get_voice(self, voice_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/voices/{voice_id}").json()

    def update_voice(
        self,
        voice_id: str,
        *,
        name: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        remove_background_noise: bool | None = None,
    ) -> dict[str, Any]:
        files: list[tuple[str, tuple[None, str]]] = [("name", (None, name))]
        if description:
            files.append(("description", (None, description)))
        if labels:
            files.append(("labels", (None, json.dumps(labels))))
        if remove_background_noise is not None:
            files.append(("remove_background_noise", (None, str(remove_background_noise).lower())))
        return self._request("POST", f"/v1/voices/{voice_id}/edit", files=files).json()

    def delete_voice(self, voice_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/voices/{voice_id}").json()

    def get_voice_settings(self, voice_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/voices/{voice_id}/settings").json()

    def update_voice_settings(self, voice_id: str, settings: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"/v1/voices/{voice_id}/settings/edit", json_body=settings).json()

    def create_ivc_voice(
        self,
        *,
        name: str,
        sample_paths: list[Path],
        description: str = "",
        labels: dict[str, str] | None = None,
        remove_background_noise: bool = False,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": name,
            "remove_background_noise": str(remove_background_noise).lower(),
        }
        if description:
            data["description"] = description
        if labels:
            data["labels"] = json.dumps(labels)

        handles: list[Any] = []
        files: list[tuple[str, tuple[str, Any, str]]] = []
        try:
            for sample_path in sample_paths:
                mime_type = mimetypes.guess_type(sample_path.name)[0] or "application/octet-stream"
                handle = sample_path.open("rb")
                handles.append(handle)
                files.append(("files", (sample_path.name, handle, mime_type)))
            return self._request("POST", "/v1/voices/add", data=data, files=files).json()
        finally:
            for handle in handles:
                handle.close()

    def create_pvc_voice(
        self,
        *,
        name: str,
        language: str,
        description: str = "",
        labels: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name, "language": language}
        if description:
            payload["description"] = description
        if labels:
            payload["labels"] = labels
        return self._request("POST", "/v1/voices/pvc", json_body=payload).json()

    def update_pvc_voice(
        self,
        voice_id: str,
        *,
        name: str | None = None,
        language: str | None = None,
        description: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if language is not None:
            payload["language"] = language
        if description is not None:
            payload["description"] = description
        if labels is not None:
            payload["labels"] = labels
        return self._request("POST", f"/v1/voices/pvc/{voice_id}", json_body=payload).json()

    def add_pvc_samples(
        self,
        voice_id: str,
        *,
        sample_paths: list[Path],
        remove_background_noise: bool = False,
    ) -> list[dict[str, Any]]:
        handles: list[Any] = []
        files: list[tuple[str, tuple[str, Any, str]]] = []
        try:
            for sample_path in sample_paths:
                mime_type = mimetypes.guess_type(sample_path.name)[0] or "application/octet-stream"
                handle = sample_path.open("rb")
                handles.append(handle)
                files.append(("files", (sample_path.name, handle, mime_type)))
            return self._request(
                "POST",
                f"/v1/voices/pvc/{voice_id}/samples",
                data={"remove_background_noise": str(remove_background_noise).lower()},
                files=files,
            ).json()
        finally:
            for handle in handles:
                handle.close()

    def update_pvc_sample(
        self,
        voice_id: str,
        sample_id: str,
        *,
        remove_background_noise: bool | None = None,
        selected_speaker_ids: list[str] | None = None,
        trim_start_time: int | None = None,
        trim_end_time: int | None = None,
        file_name: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if remove_background_noise is not None:
            payload["remove_background_noise"] = remove_background_noise
        if selected_speaker_ids is not None:
            payload["selected_speaker_ids"] = selected_speaker_ids
        if trim_start_time is not None:
            payload["trim_start_time"] = trim_start_time
        if trim_end_time is not None:
            payload["trim_end_time"] = trim_end_time
        if file_name is not None:
            payload["file_name"] = file_name
        return self._request("POST", f"/v1/voices/pvc/{voice_id}/samples/{sample_id}", json_body=payload).json()

    def get_voice_sample_audio(self, voice_id: str, sample_id: str) -> BinaryPayload:
        response = self._request("GET", f"/v1/voices/{voice_id}/samples/{sample_id}/audio", accept="*/*")
        return BinaryPayload(
            content=response.content,
            content_type=response.headers.get("content-type", "audio/mpeg"),
        )

    def get_pvc_sample_audio(self, voice_id: str, sample_id: str) -> BinaryPayload:
        response = self._request("GET", f"/v1/voices/pvc/{voice_id}/samples/{sample_id}/audio", accept="*/*")
        return BinaryPayload(
            content=response.content,
            content_type=response.headers.get("content-type", "audio/mpeg"),
        )

    def get_pvc_verification_captcha(self, voice_id: str) -> BinaryPayload:
        response = self._request("GET", f"/v1/voices/pvc/{voice_id}/captcha", accept="*/*")
        return BinaryPayload(
            content=response.content,
            content_type=response.headers.get("content-type", "image/png"),
        )

    def verify_pvc_captcha(self, voice_id: str, *, recording_path: Path) -> dict[str, Any]:
        mime_type = mimetypes.guess_type(recording_path.name)[0] or "application/octet-stream"
        with recording_path.open("rb") as handle:
            files = [("recording", (recording_path.name, handle, mime_type))]
            return self._request("POST", f"/v1/voices/pvc/{voice_id}/captcha", data={}, files=files).json()

    def request_pvc_manual_verification(
        self,
        voice_id: str,
        *,
        file_paths: list[Path],
        extra_text: str = "",
    ) -> dict[str, Any]:
        handles: list[Any] = []
        files: list[tuple[str, tuple[str, Any, str]]] = []
        try:
            for file_path in file_paths:
                mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
                handle = file_path.open("rb")
                handles.append(handle)
                files.append(("files", (file_path.name, handle, mime_type)))
            data = {"extra_text": extra_text} if extra_text else {}
            return self._request("POST", f"/v1/voices/pvc/{voice_id}/verification", data=data, files=files).json()
        finally:
            for handle in handles:
                handle.close()

    def start_pvc_training(self, voice_id: str, *, model_id: str = "eleven_multilingual_v2") -> dict[str, Any]:
        return self._request("POST", f"/v1/voices/pvc/{voice_id}/train", json_body={"model_id": model_id}).json()

    def get_shared_voices(
        self,
        *,
        page: int = 1,
        page_size: int = 24,
        search: str = "",
        category: str = "",
        gender: str = "",
        age: str = "",
        accent: str = "",
        language: str = "",
        locale: str = "",
        featured: bool | None = None,
        sort: str = "trending",
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "page_size": page_size, "sort": sort}
        if search:
            params["search"] = search
        if category:
            params["category"] = category
        if gender:
            params["gender"] = gender
        if age:
            params["age"] = age
        if accent:
            params["accent"] = accent
        if language:
            params["language"] = language
        if locale:
            params["locale"] = locale
        if featured is not None:
            params["featured"] = str(featured).lower()
        return self._request("GET", "/v1/shared-voices", params=params).json()

    def add_shared_voice(
        self,
        *,
        public_user_id: str,
        voice_id: str,
        new_name: str,
        bookmarked: bool = True,
    ) -> dict[str, Any]:
        payload = {"new_name": new_name, "bookmarked": bookmarked}
        return self._request(
            "POST",
            f"/v1/voices/add/{public_user_id}/{voice_id}",
            json_body=payload,
        ).json()

    def list_dubs(
        self,
        *,
        cursor: str = "",
        page_size: int = 100,
        dubbing_status: str = "",
        filter_by_creator: str = "all",
        order_by: str = "created_at",
        order_direction: str = "DESCENDING",
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "page_size": page_size,
            "filter_by_creator": filter_by_creator,
            "order_by": order_by,
            "order_direction": order_direction,
        }
        if cursor:
            params["cursor"] = cursor
        if dubbing_status:
            params["dubbing_status"] = dubbing_status
        return self._request("GET", "/v1/dubbing", params=params).json()

    def create_dubbing(
        self,
        *,
        target_lang: str,
        source_lang: str = "auto",
        name: str = "",
        source_url: str = "",
        file_path: Path | None = None,
        num_speakers: int = 0,
        watermark: bool = False,
        highest_resolution: bool = False,
        drop_background_audio: bool = False,
        use_profanity_filter: bool = False,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "target_lang": target_lang,
            "source_lang": source_lang or "auto",
            "num_speakers": str(max(0, int(num_speakers))),
            "watermark": str(bool(watermark)).lower(),
            "highest_resolution": str(bool(highest_resolution)).lower(),
            "drop_background_audio": str(bool(drop_background_audio)).lower(),
            "use_profanity_filter": str(bool(use_profanity_filter)).lower(),
        }
        if name:
            data["name"] = name
        if source_url:
            data["source_url"] = source_url

        files: list[tuple[str, tuple[str, Any, str]]] | None = None
        handle = None
        try:
            if file_path is not None:
                mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
                handle = file_path.open("rb")
                files = [("file", (file_path.name, handle, mime_type))]
            return self._request("POST", "/v1/dubbing", data=data, files=files).json()
        finally:
            if handle is not None:
                handle.close()

    def get_dubbing(self, dubbing_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/dubbing/{dubbing_id}").json()

    def get_dubbed_audio(self, dubbing_id: str, language_code: str) -> BinaryPayload:
        response = self._request("GET", f"/v1/dubbing/{dubbing_id}/audio/{language_code}", accept="*/*")
        return BinaryPayload(
            content=response.content,
            content_type=response.headers.get("content-type", "audio/mpeg"),
        )

    def delete_dubbing(self, dubbing_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/dubbing/{dubbing_id}").json()

    def list_studio_projects(self) -> dict[str, Any]:
        return self._request("GET", "/v1/studio/projects").json()

    def get_studio_project(self, project_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/studio/projects/{project_id}").json()

    def create_studio_project(
        self,
        *,
        name: str,
        default_model_id: str = "",
        default_title_voice_id: str = "",
        default_paragraph_voice_id: str = "",
        from_url: str = "",
        from_document_path: Path | None = None,
        quality_preset: str = "",
        auto_convert: bool = False,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {"name": name, "auto_convert": str(bool(auto_convert)).lower()}
        if default_model_id:
            data["default_model_id"] = default_model_id
        if default_title_voice_id:
            data["default_title_voice_id"] = default_title_voice_id
        if default_paragraph_voice_id:
            data["default_paragraph_voice_id"] = default_paragraph_voice_id
        if from_url:
            data["from_url"] = from_url
        if quality_preset:
            data["quality_preset"] = quality_preset

        files: list[tuple[str, tuple[str, Any, str]]] | None = None
        handle = None
        try:
            if from_document_path is not None:
                mime_type = mimetypes.guess_type(from_document_path.name)[0] or "application/octet-stream"
                handle = from_document_path.open("rb")
                files = [("from_document", (from_document_path.name, handle, mime_type))]
            return self._request("POST", "/v1/studio/projects", data=data, files=files).json()
        finally:
            if handle is not None:
                handle.close()

    def delete_studio_project(self, project_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/studio/projects/{project_id}").json()

    def convert_studio_project(self, project_id: str) -> dict[str, Any]:
        return self._request("POST", f"/v1/studio/projects/{project_id}/convert").json()

    def list_studio_project_snapshots(self, project_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/studio/projects/{project_id}/snapshots").json()

    def stream_studio_project_archive(
        self,
        project_id: str,
        project_snapshot_id: str,
    ) -> BinaryPayload:
        response = self._request(
            "POST",
            f"/v1/studio/projects/{project_id}/snapshots/{project_snapshot_id}/archive",
            json_body={},
            accept="*/*",
        )
        return BinaryPayload(
            content=response.content,
            content_type=response.headers.get("content-type", "application/zip"),
        )

    def list_studio_chapters(self, project_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/studio/projects/{project_id}/chapters").json()

    def convert_studio_chapter(self, project_id: str, chapter_id: str) -> dict[str, Any]:
        return self._request("POST", f"/v1/studio/projects/{project_id}/chapters/{chapter_id}/convert").json()

    def list_studio_chapter_snapshots(self, project_id: str, chapter_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/studio/projects/{project_id}/chapters/{chapter_id}/snapshots").json()

    def stream_studio_chapter_audio(
        self,
        project_id: str,
        chapter_id: str,
        chapter_snapshot_id: str,
        *,
        convert_to_mpeg: bool = False,
    ) -> BinaryPayload:
        response = self._request(
            "POST",
            f"/v1/studio/projects/{project_id}/chapters/{chapter_id}/snapshots/{chapter_snapshot_id}/stream",
            json_body={"convert_to_mpeg": bool(convert_to_mpeg)},
            accept="*/*",
        )
        return BinaryPayload(
            content=response.content,
            content_type=response.headers.get("content-type", "audio/mpeg"),
        )

    def text_to_speech(
        self,
        *,
        voice_id: str,
        text: str,
        model_id: str,
        output_format: str = "mp3_44100_128",
        language_code: str = "",
        seed: int | None = None,
        enable_logging: bool = True,
        voice_settings: dict[str, Any] | None = None,
        previous_text: str = "",
        next_text: str = "",
        previous_request_ids: list[str] | None = None,
        next_request_ids: list[str] | None = None,
    ) -> AudioPayload:
        params = {
            "output_format": output_format,
            "enable_logging": str(enable_logging).lower(),
        }
        payload: dict[str, Any] = {"text": text, "model_id": model_id}
        if language_code:
            payload["language_code"] = language_code
        if seed is not None:
            payload["seed"] = seed
        if voice_settings:
            payload["voice_settings"] = voice_settings
        if previous_text:
            payload["previous_text"] = previous_text
        if next_text:
            payload["next_text"] = next_text
        if previous_request_ids:
            payload["previous_request_ids"] = previous_request_ids[:3]
        if next_request_ids:
            payload["next_request_ids"] = next_request_ids[:3]

        response = self._request(
            "POST",
            f"/v1/text-to-speech/{voice_id}",
            params=params,
            json_body=payload,
            accept="*/*",
        )
        return AudioPayload(
            audio=response.content,
            content_type=response.headers.get("content-type", "audio/mpeg"),
            request_id=response.headers.get("request-id", ""),
            character_count=response.headers.get("x-character-count", ""),
            history_item_id=response.headers.get("history-item-id", ""),
        )

    def speech_to_speech(
        self,
        *,
        voice_id: str,
        audio_path: Path,
        model_id: str,
        output_format: str = "mp3_44100_128",
        seed: int | None = None,
        enable_logging: bool = True,
        voice_settings: dict[str, Any] | None = None,
    ) -> AudioPayload:
        params = {
            "output_format": output_format,
            "enable_logging": str(enable_logging).lower(),
        }
        data: dict[str, Any] = {"model_id": model_id}
        if seed is not None:
            data["seed"] = seed
        if voice_settings:
            data["voice_settings"] = json.dumps(voice_settings)

        mime_type = mimetypes.guess_type(audio_path.name)[0] or "application/octet-stream"
        with audio_path.open("rb") as handle:
            files = [("audio", (audio_path.name, handle, mime_type))]
            response = self._request(
                "POST",
                f"/v1/speech-to-speech/{voice_id}",
                params=params,
                data=data,
                files=files,
                accept="*/*",
            )
        return AudioPayload(
            audio=response.content,
            content_type=response.headers.get("content-type", "audio/mpeg"),
            request_id=response.headers.get("request-id", ""),
            character_count=response.headers.get("x-character-count", ""),
            history_item_id=response.headers.get("history-item-id", ""),
        )

    def get_history(
        self,
        *,
        page_size: int = 20,
        start_after_history_item_id: str = "",
        voice_id: str = "",
        model_id: str = "",
        search: str = "",
        source: str = "",
        sort_direction: str = "desc",
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page_size": page_size, "sort_direction": sort_direction}
        if start_after_history_item_id:
            params["start_after_history_item_id"] = start_after_history_item_id
        if voice_id:
            params["voice_id"] = voice_id
        if model_id:
            params["model_id"] = model_id
        if search:
            params["search"] = search
        if source:
            params["source"] = source
        return self._request("GET", "/v1/history", params=params).json()

    def get_history_audio(self, history_item_id: str, *, output_format: str = "") -> AudioPayload:
        params = {"output_format": output_format} if output_format else None
        response = self._request(
            "GET",
            f"/v1/history/{history_item_id}/audio",
            params=params,
            accept="*/*",
        )
        return AudioPayload(
            audio=response.content,
            content_type=response.headers.get("content-type", "audio/mpeg"),
            request_id=response.headers.get("request-id", ""),
            character_count=response.headers.get("x-character-count", ""),
            history_item_id=history_item_id,
        )

    def delete_history_item(self, history_item_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/history/{history_item_id}").json()
