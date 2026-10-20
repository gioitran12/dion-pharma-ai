import urllib.request
import urllib.parse
import json
import ssl
from typing import Dict, Any, List, Optional

DEFAULT_USER_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiODQ5Njk2NDk4NDEiLCJleHAiOjE4MDAyNDQ4OTksImFwcGxpY2F0aW9uIjoxLCJ1aWQiOiJhNWFlZTM1ZS02NjA5LTQyMTEtYmQxYy0yMmY3Mzc3OTEwZTciLCJzZXNzaW9uX2lkIjoiZTA5MzM1YWItMjg5NS00MjZkLTg5NjctYWM5OWYxMzkxZjM0IiwiaWF0IjoxNzkyNDY4ODk5LCJwYW5jYWtlX2lkIjoiZjhlYTZmMmMtZjVmYy00MTBjLWI3ODctNzViNjIzZjM4ZDdjIiwiZmJfaWQiOm51bGwsImxvZ2luX3Nlc3Npb24iOm51bGwsImZiX25hbWUiOiI4NDk2OTY0OTg0MSJ9.N1zxwZfoA3pi-dhsDnVPHJB4N1lMmaJukAfQEOJ052A"

DEFAULT_PAGE_ACCESS_TOKENS = {
    "igo_17841436773289596": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Imlnb18xNzg0MTQzNjc3MzI4OTU5NiIsInRpbWVzdGFtcCI6MTc5MjQ4MDcyMH0.l8zhRaSXpvWi2yYi5J4zz4x7_6WBV3C0SfuclRFrlxI",
    "ttm_-000unZMd77nKbLHeDFBp_YTTOoZ3zMqdilt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6InR0bV8tMDAwdW5aTWQ3N25LYkxIZURGQnBfWVRUT29aM3pNcWRpbHQiLCJ0aW1lc3RhbXAiOjE3OTI0ODA3ODd9.UCCAsFG1WPNv3j_12PnibHCgGmCJnvdaGAgYESqLsu0"
}


class PancakeClient:
    """
    Client tich hop Pancake Open API (pos.pages.fm / pages.fm)
    Ket noi du lieu don hang, kho hang, khach hang va dong bo da kenh voi Vistafa.
    """
    BASE_POS_URL = "https://pos.pages.fm/api/v1"

    def __init__(
        self,
        api_key: str = "57d1deca6acd500213ef572b272d2852",
        shop_id: Optional[int] = 1943149040,
        user_access_token: Optional[str] = None
    ):
        self.api_key = api_key
        self.shop_id = shop_id
        self.user_access_token = user_access_token or DEFAULT_USER_ACCESS_TOKEN
        self.page_access_tokens = dict(DEFAULT_PAGE_ACCESS_TOKENS)
        self._ctx = ssl.create_default_context()

    def set_chat_tokens(self, access_token: Optional[str] = None, page_access_token: Optional[str] = None):
        """Luu tru token chat cua Pancake Pages"""
        if access_token:
            self.user_access_token = access_token.strip()
        if page_access_token:
            # default to instagram page
            self.page_access_tokens["igo_17841436773289596"] = page_access_token.strip()

    def get_page_access_token(self, page_id: str) -> Optional[str]:
        """Lay hoac tao moi Page Access Token cho tung Page tu User Access Token"""
        if page_id in self.page_access_tokens:
            return self.page_access_tokens[page_id]
        if self.user_access_token:
            url = f"https://pages.fm/api/v1/pages/{page_id}/generate_page_access_token?access_token={self.user_access_token}"
            try:
                req = urllib.request.Request(url, method="POST", data=b"", headers={"User-Agent": "VistafaClient/1.0"})
                with urllib.request.urlopen(req, timeout=10, context=self._ctx) as r:
                    res = json.loads(r.read().decode())
                    if res.get("success") and res.get("page_access_token"):
                        self.page_access_tokens[page_id] = res["page_access_token"]
                        return res["page_access_token"]
            except Exception:
                pass
        return None

    def get_conversations(self, page_id: str = "igo_17841436773289596", page_number: int = 1) -> Dict[str, Any]:
        """
        Lay danh sach cuoc hoi thoai tu Pancake Pages Chat API (public_api/v2)
        """
        pat = self.get_page_access_token(page_id)
        if not pat:
            return {
                "success": False,
                "needs_token": True,
                "message": "Chua co Page Access Token hop le cho trang nay."
            }

        url = f"https://pages.fm/api/public_api/v2/pages/{page_id}/conversations?page_access_token={pat}"
        headers = {"User-Agent": "VistafaClient/1.0", "Accept": "application/json"}
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=12, context=self._ctx) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_messages(self, page_id: str, conversation_id: str) -> Dict[str, Any]:
        """
        Lay noi dung tin nhan chi tiet cua mot cuoc hoi thoai tu Pancake Pages (public_api/v1)
        """
        pat = self.get_page_access_token(page_id)
        if not pat:
            return {"success": False, "message": "Chua co Page Access Token"}
        url = f"https://pages.fm/api/public_api/v1/pages/{page_id}/conversations/{conversation_id}/messages?page_access_token={pat}"
        headers = {"User-Agent": "VistafaClient/1.0", "Accept": "application/json"}
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=12, context=self._ctx) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sync_live_to_conversation_manager(self, cm) -> Dict[str, Any]:
        """
        Quet cac cuoc hoi thoai thuc te tu Pancake Pages va dong bo thang vao LiveConversationManager.
        """
        import re, html
        def clean_html(text):
            if not text:
                return ""
            unescaped = html.unescape(re.sub(r"<[^<]+?>", "", text)).strip()
            # Absolute zero emojis standard: strip emoji unicode ranges
            clean_text = re.sub(r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\u3030\u303d\u3297\u3299]", "", unescaped)
            return clean_text.strip()

        pages_to_sync = [
            ("igo_17841436773289596", "instagram", "[IG] Instagram (Pancake Live)"),
            ("ttm_-000unZMd77nKbLHeDFBp_YTTOoZ3zMqdilt", "tiktok", "[TIKTOK] TikTok Shop (Pancake Live)")
        ]
        total_synced = 0
        synced_convs = []

        for pid, channel_code, channel_lbl in pages_to_sync:
            convs_res = self.get_conversations(page_id=pid)
            if not convs_res.get("success"):
                continue
            for c in convs_res.get("conversations", []):
                cid = c.get("id")
                cust_info = c.get("from", {}) or {}
                cust_name = cust_info.get("name") or cust_info.get("username") or "Khách hàng Pancake"
                snippet = clean_html(c.get("snippet", ""))

                # fetch messages for this conversation
                m_res = self.get_messages(pid, cid)
                raw_msgs = m_res.get("messages", []) if m_res.get("success") else []
                parsed_msgs = []
                for rm in reversed(raw_msgs):
                    raw_text = clean_html(rm.get("message", ""))
                    if not raw_text:
                        continue
                    sender_type = "agent" if (rm.get("from", {}).get("id") == pid or "tdgioi" in rm.get("from", {}).get("name", "")) else "customer"
                    ins_time = rm.get("inserted_at", "")
                    time_display = ins_time[11:16] if len(ins_time) >= 16 else "14:05"
                    parsed_msgs.append({
                        "sender": sender_type,
                        "text": raw_text,
                        "time": time_display
                    })

                if not parsed_msgs and snippet:
                    parsed_msgs.append({"sender": "customer", "text": snippet, "time": "14:05"})

                # Extract phone number if found
                phone_match = re.search(r"(?:0|\+84)\d{9,10}", "\n".join([m["text"] for m in parsed_msgs]))
                phone_num = phone_match.group(0) if phone_match else ""

                # Determine lead priority and product
                lead_priority = "HOT" if len(parsed_msgs) > 2 else "WARM"
                product_id = "calcium_complex" if "muay" in cust_name.lower() else "beauty_collagen"
                product_name = "VitGarden Calcium Complex" if product_id == "calcium_complex" else "Beauty Collagen Powder"

                # internal ID for manager
                safe_conv_id = f"PANCAKE-{pid[-6:]}-{cid[-6:]}"
                conv_data = {
                    "id": safe_conv_id,
                    "pancake_conv_id": cid,
                    "customer_name": cust_name,
                    "channel": channel_code,
                    "channel_label": channel_lbl,
                    "phone": phone_num,
                    "product_id": product_id,
                    "product_name": product_name,
                    "status": "ACTIVE",
                    "lead_priority": lead_priority,
                    "intent": f"Tin nhắn thực tế từ Pancake ({cust_name})",
                    "clinical_profile": {"notes": f"Đồng bộ trực tiếp qua Pancake Open API từ {channel_lbl}"},
                    "messages": parsed_msgs,
                    "updated_at": c.get("updated_at", "")[:16].replace("T", " "),
                    "pancake_metadata": {
                        "shop_id": self.shop_id,
                        "shop_name": "Trần Giỏi",
                        "page_id": pid,
                        "conversation_id": cid,
                        "snippet": snippet
                    }
                }
                cm._conversations[safe_conv_id] = conv_data
                synced_convs.append(conv_data)
                total_synced += 1

        return {
            "success": True,
            "total_synced": total_synced,
            "conversations": synced_convs,
            "message": f"Đã đồng bộ thành công {total_synced} cuộc hội thoại thực tế từ Pancake."
        }

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
