from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class ShopKnowledgeAnswer:
    topic: str
    answer: str


@dataclass(frozen=True)
class _KnowledgeRecord:
    topic: str
    phrases: tuple[str, ...]
    answer: str


_RECORDS: tuple[_KnowledgeRecord, ...] = (
    _KnowledgeRecord(
        "return_and_warranty_policy",
        ("doi tra va bao hanh", "doi tra bao hanh"),
        "Theo chính sách của Mystery Closet, sản phẩm đủ điều kiện được đổi trả trong 07 ngày "
        "kể từ ngày nhận hàng. Thời hạn bảo hành là 30 ngày với quần áo và phụ kiện, 60 ngày "
        "với giày dép, tính từ ngày mua. Sản phẩm cần còn tem nhãn, chưa qua sử dụng và có thể "
        "xác minh thông tin mua hàng.",
    ),
    _KnowledgeRecord(
        "shipping_fee_policy",
        (
            "phi van chuyen",
            "phi giao hang",
            "phi ship",
            "tien ship",
            "freeship",
            "free ship",
            "mien phi van chuyen",
            "mien phi giao hang",
        ),
        "Theo Chính sách vận chuyển: phí tiêu chuẩn là 20.000đ tại nội thành Hà Nội/TP.HCM, "
        "30.000đ tại các tỉnh thành khác và 40.000đ - 60.000đ tại miền núi/hải đảo. Shop miễn "
        "phí vận chuyển từ 500.000đ tại nội thành Hà Nội/TP.HCM, hoặc từ 1.000.000đ toàn quốc "
        "(không áp dụng miền núi/hải đảo). Vì vậy đơn dưới 100.000đ không thuộc các ngưỡng "
        "freeship đã công bố.",
    ),
    _KnowledgeRecord(
        "express_shipping_policy",
        ("giao hoa toc", "ship hoa toc", "giao trong ngay", "giao trong 10 phut"),
        "Shop có giao hỏa tốc trong ngày tại nội thành Hà Nội và TP.HCM, phí từ 50.000đ đến "
        "100.000đ. Chính sách không công bố dịch vụ giao trong 10 phút.",
    ),
    _KnowledgeRecord(
        "order_tracking",
        ("theo doi don hang", "theo doi don", "ma van don", "kiem tra don hang"),
        "Bạn có thể theo dõi đơn trong mục “Đơn hàng của tôi”, qua mã vận đơn/đường dẫn trong "
        "email xác nhận, hoặc liên hệ CSKH qua hotline 1900 1340. Đơn thường được xử lý trong "
        "24 giờ làm việc sau khi xác nhận.",
    ),
    _KnowledgeRecord(
        "shipping_time_policy",
        (
            "giao trong bao lau",
            "bao lau thi giao",
            "bao lau nhan hang",
            "khi nao nhan hang",
            "thoi gian giao hang",
            "thoi gian van chuyen",
        ),
        "Sau khi bàn giao cho đơn vị vận chuyển, thời gian dự kiến là 1-2 ngày làm việc ở nội "
        "thành Hà Nội/TP.HCM, 3-5 ngày ở các tỉnh thành khác và 5-7 ngày tại miền núi, hải đảo. "
        "Đơn hàng được xử lý trong 24 giờ làm việc; dịp cao điểm có thể tối đa 48 giờ.",
    ),
    _KnowledgeRecord(
        "shipping_carriers",
        (
            "don vi van chuyen",
            "hang van chuyen",
            "ben van chuyen",
            "ship bang gi",
            "ghn",
            "ghtk",
            "viettel post",
            "j&t",
            "ninja van",
        ),
        "Mystery Closet công bố các đối tác vận chuyển gồm GHN, GHTK, Viettel Post, J&T "
        "Express và Ninja Van. Shop sẽ chọn đơn vị phù hợp theo địa chỉ và loại sản phẩm.",
    ),
    _KnowledgeRecord(
        "warranty_policy",
        ("bao hanh", "thoi han bao hanh", "loi duong may", "loi khoa keo"),
        "Theo Chính sách bảo hành của Mystery Closet: quần áo và phụ kiện được bảo hành 30 "
        "ngày, giày dép 60 ngày kể từ ngày mua. Phạm vi gồm lỗi đường may, nút/khóa, bạc màu "
        "hoặc co rút/xù lông bất thường trong điều kiện sử dụng và bảo quản bình thường; kết "
        "quả kiểm tra được thông báo trong 3-5 ngày làm việc.",
    ),
    _KnowledgeRecord(
        "return_policy",
        ("doi tra", "doi hang", "tra hang", "hoan tien", "doi size", "doi kich co"),
        "Theo Chính sách đổi trả, bạn có thể yêu cầu đổi trả trong 07 ngày kể từ ngày nhận hàng "
        "nếu sản phẩm còn tem nhãn, chưa sử dụng/giặt ủi, không hư hỏng do người dùng và có thể "
        "xác minh việc mua hàng. Mỗi đơn được đổi trả 01 lần; hàng giảm trên 30% chỉ được đổi "
        "size nếu còn hàng và không áp dụng trả hàng hoàn tiền.",
    ),
    _KnowledgeRecord(
        "payment_methods",
        (
            "phuong thuc thanh toan",
            "thanh toan bang",
            "cach thanh toan",
            "cod",
            "chuyen khoan",
            "visa",
            "mastercard",
            "momo",
            "zalopay",
            "vnpay",
            "qr code",
        ),
        "Mystery Closet hỗ trợ thanh toán khi nhận hàng (COD), chuyển khoản ngân hàng, thẻ "
        "Visa/MasterCard/JCB, ví MoMo/ZaloPay/VNPay và QR Code. Thông tin chuyển khoản được "
        "cung cấp sau khi bạn đặt hàng.",
    ),
    _KnowledgeRecord(
        "privacy_policy",
        (
            "chinh sach bao mat",
            "bao mat thong tin",
            "du lieu ca nhan",
            "thong tin ca nhan",
            "quyen rieng tu",
            "cookie",
        ),
        "Chính sách bảo mật của Mystery Closet nêu việc thu thập thông tin tài khoản, liên hệ, "
        "giao nhận/thanh toán và dữ liệu sử dụng website để xử lý đơn, chăm sóc khách hàng, cải "
        "thiện dịch vụ và bảo đảm an ninh. Bạn có quyền yêu cầu truy cập, chỉnh sửa, xóa hoặc "
        "hạn chế xử lý dữ liệu trong các trường hợp áp dụng; email liên hệ là "
        "privacy@mysterycloset.com.",
    ),
    _KnowledgeRecord(
        "terms_of_use",
        ("dieu khoan su dung", "dieu khoan website", "quy dinh su dung"),
        "Điều khoản sử dụng của Mystery Closet quy định về tài khoản, đặt hàng/thanh toán, tình "
        "trạng sản phẩm, quyền sở hữu trí tuệ, hành vi bị cấm và giới hạn trách nhiệm. Đơn chỉ "
        "được xác nhận khi shop gửi email xác nhận; phí vận chuyển được hiển thị riêng khi thanh "
        "toán. Liên hệ pháp lý: legal@mysterycloset.com.",
    ),
    _KnowledgeRecord(
        "purchase_guide",
        (
            "huong dan mua hang",
            "cach mua hang",
            "cach dat hang",
            "dat hang nhu the nao",
            "lam sao de mua",
        ),
        "Để mua hàng, bạn tìm và mở sản phẩm, chọn màu/size/số lượng, thêm vào giỏ, chọn “Tiến "
        "hành thanh toán”, điền thông tin giao hàng, chọn vận chuyển và thanh toán, sau đó xem "
        "lại rồi bấm “Đặt hàng”. Shop khuyến khích tạo tài khoản để dễ theo dõi đơn.",
    ),
    _KnowledgeRecord(
        "policy_overview",
        ("shop co chinh sach gi", "cac chinh sach", "chinh sach cua shop"),
        "Mystery Closet hiện công bố: Chính sách đổi trả và bảo hành, Chính sách vận chuyển, "
        "Chính sách bảo mật, Điều khoản sử dụng và Hướng dẫn mua hàng. Bạn muốn mình trình bày "
        "phần nào?",
    ),
    _KnowledgeRecord(
        "social_channels",
        (
            "facebook cua shop",
            "instagram cua shop",
            "tiktok cua shop",
            "youtube cua shop",
            "mang xa hoi cua shop",
            "ket noi voi shop",
        ),
        "Bạn có thể kết nối với Mystery Closet qua Facebook, Instagram, TikTok và YouTube từ "
        "các biểu tượng “Kết nối với chúng tôi” ở footer website.",
    ),
    _KnowledgeRecord(
        "contact_information",
        (
            "hotline",
            "so dien thoai shop",
            "so dien thoai cua shop",
            "so dien thoai cskh",
            "email shop",
            "email cua shop",
            "email cskh",
            "dia chi shop",
            "dia chi cua shop",
            "dia chi cua hang",
            "shop o dau",
            "cua hang o dau",
            "gio lam viec",
            "thoi gian lam viec",
            "lien he shop",
            "thong tin lien he",
        ),
        "Thông tin liên hệ của Mystery Closet: hotline 1900 1340 (8:00 - 21:00), email "
        "cskh@mysterycloset.com, địa chỉ 260 Lý Thường Kiệt, Phường 14, Quận 10, TP. HCM, "
        "Việt Nam. Shop làm việc từ 8:00 đến 21:00 tất cả các ngày.",
    ),
    _KnowledgeRecord(
        "legal_information",
        (
            "ma so thue",
            "ma so doanh nghiep",
            "so dkkd",
            "dang ky kinh doanh",
            "ten cong ty",
            "cong ty nao van hanh",
            "thong tin phap ly",
        ),
        "Đơn vị được ghi ở footer là Công ty TNHH Thời Trang Mystery Closet, mã số thuế "
        "0123456789, số ĐKKD 0123456789 do Sở KH&ĐT TP.HCM cấp ngày 01/01/2025; website ghi "
        "nhận đã thông báo với Bộ Công Thương.",
    ),
    _KnowledgeRecord(
        "shop_identity",
        (
            "ten shop",
            "shop ten gi",
            "ten cua shop",
            "ten cua hang",
            "cua hang ten gi",
            "shop minh co ten gi",
            "day la shop gi",
            "ban la shop nao",
        ),
        "Shop có tên là Mystery Closet (trang giới thiệu dùng tên Mystery Closet Store). Đơn "
        "vị được ghi ở footer là Công ty TNHH Thời Trang Mystery Closet.",
    ),
    _KnowledgeRecord(
        "shop_about",
        (
            "gioi thieu ve shop",
            "gioi thieu cua hang",
            "mystery closet la gi",
            "shop ban gi",
            "shop kinh doanh gi",
        ),
        "Mystery Closet Store là thương hiệu thời trang và chăm sóc cá nhân, cung cấp các sản "
        "phẩm thời trang nam nữ được chọn lọc, hướng đến phong cách tinh tế, hiện đại và trải "
        "nghiệm chăm sóc khách hàng tận tâm.",
    ),
)


def resolve_shop_knowledge(message: str) -> ShopKnowledgeAnswer | None:
    query = _normalize(message)
    if _asks_catalog_overview(query):
        return ShopKnowledgeAnswer(topic="catalog_overview", answer="")
    asks_identity = _asks_shop_identity(query)
    asks_location = _asks_shop_location(query)
    if asks_identity and asks_location:
        return ShopKnowledgeAnswer(
            topic="shop_identity_and_location",
            answer=(
                "Shop có tên là Mystery Closet (trang giới thiệu dùng tên Mystery Closet Store). "
                "Địa chỉ shop là 260 Lý Thường Kiệt, Phường 14, Quận 10, TP. HCM, Việt Nam."
            ),
        )
    if asks_identity:
        return _answer_for_topic("shop_identity")
    if asks_location:
        return _answer_for_topic("contact_information")

    padded = f" {query} "
    for record in _RECORDS:
        if any(f" {phrase} " in padded for phrase in record.phrases):
            return ShopKnowledgeAnswer(
                topic=record.topic,
                answer=_direct_policy_correction(query, record),
            )
    return None


def _direct_policy_correction(query: str, record: _KnowledgeRecord) -> str:
    if record.topic == "warranty_policy" and "tron doi" in query:
        return "Không, shop không có cam kết bảo hành trọn đời. " + record.answer
    if (
        record.topic == "return_policy"
        and "hoan tien" in query
        and re.search(r"\b200\s*(?:phan tram|%)\b", query)
    ):
        return "Không, shop không có cam kết hoàn tiền 200% trong mọi trường hợp. " + record.answer
    return record.answer


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    ascii_text = "".join(
        character for character in decomposed if unicodedata.category(character) != "Mn"
    ).replace("\u0111", "d")
    return re.sub(r"[^a-z0-9&]+", " ", ascii_text).strip()


def _asks_shop_identity(query: str) -> bool:
    mentions_shop = "shop" in query.split() or "cua hang" in query
    asks_name = any(
        phrase in query
        for phrase in ("ten la gi", "ten gi", "co ten la gi", "co ten gi")
    )
    return mentions_shop and asks_name


def _asks_catalog_overview(query: str) -> bool:
    mentions_shop = "shop" in query.split() or "cua hang" in query
    asks_products = any(
        phrase in query
        for phrase in (
            "dang ban nhung loai san pham nao",
            "ban nhung loai san pham nao",
            "dang ban san pham gi",
            "ban san pham gi",
            "co nhung loai san pham nao",
            "co nhung san pham gi",
            "co cac danh muc nao",
            "dang co danh muc gi",
        )
    )
    return mentions_shop and asks_products


def _asks_shop_location(query: str) -> bool:
    mentions_shop = "shop" in query.split() or "cua hang" in query
    asks_place = any(
        phrase in query
        for phrase in ("vi tri", "dia chi", "o dau", "nam o dau")
    )
    return mentions_shop and asks_place


def _answer_for_topic(topic: str) -> ShopKnowledgeAnswer:
    record = next(record for record in _RECORDS if record.topic == topic)
    return ShopKnowledgeAnswer(topic=record.topic, answer=record.answer)
