import urllib.request
import urllib.parse
import json
import ssl
from typing import Dict, Any, List, Optional

class PancakeClient:
    """
    Client tich hop Pancake Open API (pos.pages.fm / pages.fm)
    Ket noi du lieu don hang, kho hang, khach hang va dong bo da kenh voi Vistafa.
    """
    BASE_POS_URL = "https://pos.pages.fm/api/v1"

    def __init__(self, api_key: str = "57d1deca6acd500213ef572b272d2852", shop_id: Optional[int] = 1943149040):
        self.api_key = api_key
        self.shop_id = shop_id
        self._ctx = ssl.create_default_context()

    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        query_params = dict(params or {})
        query_params["api_key"] = self.api_key
        query_str = urllib.parse.urlencode(query_params)
        url = f"{self.BASE_POS_URL}{endpoint}?{query_str}"

        headers = {
            "User-Agent": "Vistafa-OmniClient/1.0",
            "Accept": "application/json"
        }
        encoded_data = None
        if data:
            headers["Content-Type"] = "application/json"
            encoded_data = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=12, context=self._ctx) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            return {"success": False, "error_code": e.code, "message": err_body}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_shops(self) -> Dict[str, Any]:
        """Lay danh sach Shop va cac Page/Kenh dang lien ket tren Pancake"""
        res = self._request("/shops")
        if res.get("success") and res.get("shops") and not self.shop_id:
            self.shop_id = res["shops"][0]["id"]
        return res

    def get_shop_info(self) -> Dict[str, Any]:
        """Lay thong tin chi tiet Shop dang ket noi"""
        shops_res = self.get_shops()
        if not shops_res.get("success"):
            return shops_res
        shops = shops_res.get("shops", [])
        for s in shops:
            if s.get("id") == self.shop_id:
                return {"success": True, "shop": s}
        return {"success": True, "shop": shops[0] if shops else None}

    def get_products(self, page_number: int = 1, page_size: int = 30) -> Dict[str, Any]:
        """Lay danh muc san pham tren kho Pancake POS"""
        if not self.shop_id:
            self.get_shops()
        return self._request(f"/shops/{self.shop_id}/products", {"page_number": page_number, "page_size": page_size})

    def get_orders(self, page_number: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Lay danh sach don hang tren Pancake POS"""
        if not self.shop_id:
            self.get_shops()
        return self._request(f"/shops/{self.shop_id}/orders", {"page_number": page_number, "page_size": page_size})

    def get_customers(self, page_number: int = 1, page_size: int = 30) -> Dict[str, Any]:
        """Lay danh sach khach hang tren Pancake POS"""
        if not self.shop_id:
            self.get_shops()
        return self._request(f"/shops/{self.shop_id}/customers", {"page_number": page_number, "page_size": page_size})

    def get_warehouses(self) -> Dict[str, Any]:
        """Lay danh sach kho hang tren Pancake POS"""
        if not self.shop_id:
            self.get_shops()
        return self._request(f"/shops/{self.shop_id}/warehouses")

    def test_connection(self) -> Dict[str, Any]:
        """Kiem tra trang thai ket noi API Key thuc te"""
        res = self.get_shops()
        if res.get("success") and res.get("shops"):
            shop = res["shops"][0]
            pages = shop.get("pages", [])
            return {
                "connected": True,
                "api_key_valid": True,
                "shop_id": shop.get("id"),
                "shop_name": shop.get("name"),
                "currency": shop.get("currency", "VND"),
                "total_pages": len(pages),
                "pages": [
                    {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "username": p.get("username"),
                        "platform": p.get("platform")
                    } for p in pages
                ],
                "message": "[OK] Ket noi Pancake Open API thanh cong 100%"
            }
        return {
            "connected": False,
            "api_key_valid": False,
            "message": res.get("message", "Khong the ket noi den Pancake API")
        }

    def get_pages(self) -> Dict[str, Any]:
        """Lay danh sach cac trang Fanpage FB, Instagram, TikTok Shop dang ket noi"""
        if not self.shop_id:
            self.get_shops()
        return self._request(f"/shops/{self.shop_id}/pages")

    def send_message(self, page_id: str, conversation_id: str, message_text: str) -> Dict[str, Any]:
        """
        Gui tin nhan thuc te ra app (Facebook Messenger / Instagram DM / TikTok)
        Yeu cau Page Access Token hoac Open API duoc cap quyen tren Pancake.
        """
        # Endpoint chuan tren Pancake Chat API
        endpoint = f"/pages/{page_id}/conversations/{conversation_id}/messages"
        payload = {
            "message": message_text,
            "action": "reply"
        }
        res = self._request(endpoint, method="POST", data=payload)
        return res

    def set_chat_tokens(self, access_token: Optional[str] = None, page_access_token: Optional[str] = None):
        """Luu tru token chat cua Pancake Pages"""
        if access_token:
            self.user_access_token = access_token.strip()
        if page_access_token:
            self.page_access_token = page_access_token.strip()

    def get_conversations(self, page_id: str = "igo_17841436773289596", page_number: int = 1) -> Dict[str, Any]:
        """
        Lay danh sach cuoc hoi thoai tu Pancake Pages Chat API (public_api/v1)
        Yeu cau page_access_token hoac access_token (User Token tu pages.fm)
        """
        token = getattr(self, "page_access_token", None) or getattr(self, "user_access_token", None)
        if not token:
            return {
                "success": False,
                "needs_token": True,
                "message": "Can ma Pancake Chat Token (API Access Token tu pages.fm -> Cai dat ca nhan) de dong bo tin nhan truc tiep."
            }

        param_key = "page_access_token" if getattr(self, "page_access_token", None) else "access_token"
        base = "https://pages.fm/api/public_api/v1" if getattr(self, "page_access_token", None) else "https://pages.fm/api/v1"
        url = f"{base}/pages/{page_id}/conversations?{param_key}={token}&page_number={page_number}"
        headers = {"User-Agent": "Vistafa-OmniClient/1.0", "Accept": "application/json"}
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=12, context=self._ctx) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            return {"success": False, "error": str(e)}

    def handle_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tiep nhan su kien Webhook thoi gian thuc tu Pancake (tin nhan moi, don hang moi)
        """
        event_type = event_data.get("event", "message_created")
        return {
            "success": True,
            "event_processed": event_type,
            "timestamp": event_data.get("timestamp")
        }

_pancake_client_instance = None

def get_pancake_client(api_key: str = "57d1deca6acd500213ef572b272d2852") -> PancakeClient:
    global _pancake_client_instance
    if _pancake_client_instance is None or _pancake_client_instance.api_key != api_key:
        _pancake_client_instance = PancakeClient(api_key=api_key)
    return _pancake_client_instance
