import streamlit as st
import numpy as np
import os
import re
from io import BytesIO
from pathlib import Path
from PIL import Image
from Authentication import is_authenticated, login_screen
from data_backend import (
    add_clothing_item,
    delete_clothing_item,
    get_user_catalog,
    update_clothing_item,
)

try:
    import cv2
except Exception:
    cv2 = None


CLOTH_TYPE_OPTIONS = [
    '👕 T-Shirt',
    '🧥 Blazer',
    '👗 Dress',
    '🧥 Jacket',
    '🥼 Coat',
    '🧥 Hoodie',
    '🧶 Sweater',
    '🩲 Shorts',
    '👗 Skirt',
    '👖 Jeans',
    '👖 Pants',
    '🧢 Hat',
    '🕶️ Sunglasses',
    '🧣 Scarf',
    '🧤 Gloves',
]

CATEGORY_BY_CLOTH_TYPE = {
    '👕 T-Shirt': 'Top 👚',
    '👕 Shirt': 'Top 👚',
    '👗 Dress': 'Top 👚',
    '🧶 Sweater': 'Top 👚',
    '🩲 Shorts': 'Bottom 🩳',
    '👗 Skirt': 'Bottom 🩳',
    '👖 Jeans': 'Bottom 🩳',
    '👖 Pants': 'Bottom 🩳',
    '🧥 Blazer': 'Outerwear 🧥',
    '🧥 Jacket': 'Outerwear 🧥',
    '🥼 Coat': 'Outerwear 🧥',
    '🧥 Hoodie': 'Outerwear 🧥',
    '🧢 Hat': 'Accessories ⌚',
    '🕶️ Sunglasses': 'Accessories ⌚',
    '🧣 Scarf': 'Accessories ⌚',
    '🧤 Gloves': 'Accessories ⌚',
}

CATEGORY_CONFIDENCE_THRESHOLD = 0.55

if not is_authenticated():
    login_screen(
        title='Sign in to access your wardrobe',
        description='Use Google or your local email/password account to continue.',
    )
    st.stop()

# CSS animations
st.html("""
<style>
/* Shared settle animation used across pages */
@keyframes fadeSlideDownSettle {
    0% {
        opacity: 0;
        transform: translateY(-20px);
    }
    60% {
        opacity: 1;
        transform: translateY(4px);
    }
    100% {
        opacity: 1;
        transform: translateY(0);
    }
}

.wardrobe-title {
    margin: 0;
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
}

/* Buttons */
div[data-testid="stButton"] button {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

/* Grid columns */
div[data-testid="stColumn"] {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
    transition: transform 0.28s ease, box-shadow 0.28s ease;
}

div[data-testid="stColumn"]:hover {
    transform: translateY(-6px) scale(1.01);
    box-shadow: 0 18px 34px rgba(0, 0, 0, 0.16);
}

/* Divider */
div[data-testid="stDivider"] {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) 0.3s both;
}

/* Inputs and forms */
div[data-testid="stTextInput"],
div[data-testid="stSelectbox"],
div[data-testid="stFileUploader"],
div[data-testid="stColorPicker"],
div[data-testid="stForm"] {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
}

/* Markdown/text blocks */
div[data-testid="stMarkdownContainer"] {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
}

/* Stagger for buttons */
div[data-testid="stButton"]:nth-child(1) button { animation-delay: 0.0s; }
div[data-testid="stButton"]:nth-child(2) button { animation-delay: 0.1s; }
div[data-testid="stButton"]:nth-child(3) button { animation-delay: 0.2s; }
div[data-testid="stButton"]:nth-child(4) button { animation-delay: 0.3s; }

/* Stagger for grid boxes */
div[data-testid="stColumn"]:nth-child(1) { animation-delay: 0.0s; }
div[data-testid="stColumn"]:nth-child(2) { animation-delay: 0.1s; }
div[data-testid="stColumn"]:nth-child(3) { animation-delay: 0.2s; }
div[data-testid="stColumn"]:nth-child(4) { animation-delay: 0.3s; }

/* Button hover */
div[data-testid="stButton"] button:hover {
    transform: translateY(-3px) scale(1.03);
    box-shadow: 0px 12px 24px rgba(0, 0, 0, 0.22);
}

.st-key-back_button button {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) 0.1s both;
    border: 1px solid rgba(59, 130, 246, 0.35);
    transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
}

.st-key-back_button button:hover {
    transform: translateY(-3px) scale(1.03);
    box-shadow: 0 12px 24px rgba(59, 130, 246, 0.38);
    filter: brightness(1.06) saturate(1.08);
}

[class*="st-key-del"] button {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
    border: 1.5px solid rgba(239, 68, 68, 0.32) !important;
    color: #dc2626 !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease,
                background 0.18s ease, border-color 0.18s ease !important;
}

[class*="st-key-del"] button:hover {
    transform: translateY(-3px) scale(1.03);
    box-shadow: 0 12px 24px rgba(239, 68, 68, 0.4) !important;
    background: rgba(254, 226, 226, 0.88) !important;
    border-color: rgba(239, 68, 68, 0.75) !important;
    color: #b91c1c !important;
}

/* Alerts */
div[data-testid="stAlert"] {
    animation: fadeSlideDownSettle 0.8s cubic-bezier(0.34, 1.08, 0.64, 1) both;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

div[data-testid="stAlert"]:hover {
    transform: translateY(-6px);
    box-shadow: 0 14px 32px rgba(0, 0, 0, 0.14);
}

/* Sidebar should remain static (no animations) */
section[data-testid="stSidebar"] * {
    animation: none !important;
    transition: none !important;
    transform: none !important;
}

</style>
""")

# Initialize session state
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = None


GUEST_ASSET_DIR = Path(__file__).resolve().parent / 'default_clothes_guest'
GUEST_DEFAULT_ITEMS = {
    'Top 👚': [
        {
            'name': 'White T-Shirt',
            'asset': 'white t-shirt.png',
            'cloth_type': '👕 T-Shirt',
        },
        {
            'name': 'Blue Polo',
            'asset': 'blue polo.png',
            'cloth_type': '👕 T-Shirt',
        },
        {
            'name': 'Striped Shirt',
            'asset': 'stripped shirt.png',
            'cloth_type': '👕 T-Shirt',
        },
    ],
    'Bottom 🩳': [
        {
            'name': 'Chinos',
            'asset': 'chinos.png',
            'cloth_type': '👖 Pants',
        },
        {
            'name': 'Joggers',
            'asset': 'joggers.png',
            'cloth_type': '👖 Pants',
        },
        {
            'name': 'Jeans',
            'asset': 'jeans.png',
            'cloth_type': '👖 Jeans',
        },
    ],
    'Outerwear 🧥': [
        {
            'name': 'Denim Jacket',
            'asset': 'Denim jacket.png',
            'cloth_type': '🥼 Coat',
        },
        {
            'name': 'Trench Coat',
            'asset': 'Trench coat.png',
            'cloth_type': '🥼 Coat',
        },
        {
            'name': 'Puffer Vest',
            'asset': 'puffer vest.png',
            'cloth_type': '🥼 Coat',
        },
    ],
    'Accessories ⌚': [
        {
            'name': 'Leather Belt',
            'asset': 'Leather belt.png',
            'cloth_type': None,
        },
        {
            'name': 'Wool Scarf',
            'asset': 'wool scarf.png',
            'cloth_type': '🧣 Scarf',
        },
        {
            'name': 'Baseball Cap',
            'asset': 'baseball cap.png',
            'cloth_type': '🧢 Hat',
        },
    ],
}


@st.cache_data(show_spinner=False)
def _load_guest_asset_bytes(file_name: str) -> bytes | None:
    asset_path = GUEST_ASSET_DIR / file_name
    if not asset_path.exists():
        return None
    return asset_path.read_bytes()


def _ensure_catalog_categories():
    if 'catalog' not in st.session_state:
        st.session_state.catalog = {}

    for category in ('Top 👚', 'Bottom 🩳', 'Outerwear 🧥', 'Accessories ⌚'):
        st.session_state.catalog.setdefault(category, [])


def _plain_cloth_type_name(cloth_type):
    return cloth_type.split(' ', 1)[1] if ' ' in cloth_type else cloth_type


def _is_stale_media_id(value: object) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip().lower()
    return bool(re.fullmatch(r'[0-9a-f]{40,64}\.(jpg|jpeg|png|webp)', text))


def _add_item_to_catalog(
    name, cloth_type, image=None, color=None, item_id=None, conf=None
):
    _ensure_catalog_categories()

    if conf is not None and conf < CATEGORY_CONFIDENCE_THRESHOLD:
        category = 'Accessories ⌚'
    else:
        if cloth_type in ('👕 T-Shirt', '👕 Shirt', '🧶 Sweater', '👗 Dress'):
            category = 'Top 👚'
        elif cloth_type in ('👖 Shorts', '👗 Skirt', '👖 Jeans', '👖 Pants'):
            category = 'Bottom 🩳'
        else:
            category = 'Outerwear 🧥'

    item = {
        'name': name,
        'image': image,
        'color': color,
        'cloth_type': cloth_type,
    }
    if item_id is not None:
        item['id'] = item_id
    st.session_state.catalog[category].append(item)
    return category


def _set_catalog_item(old_category, item_index, updated_item, new_category):
    existing_item = st.session_state.catalog[old_category].pop(item_index)
    merged_item = {**existing_item, **updated_item}
    if new_category == old_category:
        st.session_state.catalog[old_category].insert(item_index, merged_item)
    else:
        st.session_state.catalog[new_category].insert(0, merged_item)


def _format_predicted_cloth_type(raw_label: str | None) -> str | None:
    if not raw_label:
        return None
    normalized = raw_label.strip().lower()
    mapping = {
        't-shirt': '👕 T-Shirt',
        'shirt': '👕 Shirt',
        'sweater': '🧶 Sweater',
        'dress': '👗 Dress',
        'shorts': '👖 Shorts',
        'skirt': '👗 Skirt',
        'jeans': '👖 Jeans',
        'pants': '👖 Pants',
        'blazer': '🧥 Blazer',
        'jacket': '🧥 Jacket',
        'coat': '🥼 Coat',
        'hoodie': '🧥 Hoodie',
    }
    return mapping.get(normalized, raw_label)


def _extract_image_bytes(uploaded_file) -> bytes | None:
    if uploaded_file is None:
        return None

    if isinstance(uploaded_file, np.ndarray):
        if cv2 is not None:
            success, encoded = cv2.imencode('.jpg', uploaded_file)
            if success:
                return encoded.tobytes()
            return None
        try:
            rgb_image = (
                uploaded_file[:, :, ::-1] if uploaded_file.ndim == 3 else uploaded_file
            )
            buffer = BytesIO()
            Image.fromarray(rgb_image).save(buffer, format='JPEG')
            return buffer.getvalue()
        except Exception:
            return None

    if isinstance(uploaded_file, Image.Image):
        try:
            buffer = BytesIO()
            uploaded_file.save(buffer, format='JPEG')
            return buffer.getvalue()
        except Exception:
            return None

    if isinstance(uploaded_file, (bytes, bytearray, memoryview)):
        return bytes(uploaded_file)

    if hasattr(uploaded_file, 'getvalue'):
        try:
            data = uploaded_file.getvalue()
            return bytes(data) if data else None
        except Exception:
            return None

    if hasattr(uploaded_file, 'read'):
        try:
            data = uploaded_file.read()
            return bytes(data) if data else None
        except Exception:
            return None

    return None


def addclothemedia(uploaded_file, item_name: str, local_email: str | None) -> bool:
    """Add a clothing item from uploaded media using CV classification."""
    image_data = _extract_image_bytes(uploaded_file)
    if not image_data:
        st.error(
            'Could not read image data. Please upload a valid file or capture again.'
        )
        return False

    def _add_without_cv(reason_message: str) -> bool:
        item_id = None
        if local_email:
            item_id = add_clothing_item(
                email=local_email,
                item_name=item_name,
                image_data=image_data,
            )

        category = _add_item_to_catalog(
            name=item_name,
            cloth_type=None,
            image=image_data,
            color=None,
            item_id=item_id,
            conf=0.0,
        )
        st.session_state.wardrobe_feedback = (
            f'{reason_message} Added 1 item to {category}.'
        )
        return True

    try:
        from ultralytics import YOLO
    except Exception as exc:
        error_name = type(exc).__name__
        error_message = str(exc).strip() or 'no additional details'
        return _add_without_cv(
            'Image auto-detection is unavailable in this deployment '
            f'(YOLO import failed: {error_name}: {error_message}).'
        )

    current_path = os.path.dirname(__file__)
    parent_path = os.path.dirname(current_path)
    model_dirs = [
        os.path.join(parent_path, 'computervision', 'models'),
        os.path.join(parent_path, 'models'),
        os.path.join(current_path, 'models'),
    ]

    color_cls_path = None
    category_cls_path = None
    for model_dir in model_dirs:
        candidate_color = os.path.join(model_dir, 'best_color_cls.pt')
        candidate_category = os.path.join(model_dir, 'best_category_cls.pt')
        if os.path.exists(candidate_color) and os.path.exists(candidate_category):
            color_cls_path = candidate_color
            category_cls_path = candidate_category
            break

    if not color_cls_path or not category_cls_path:
        st.error('Model files are missing. Please check the models folder.')
        return False

    if cv2 is not None:
        file_bytes = np.asarray(bytearray(image_data), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    else:
        try:
            pil_img = Image.open(BytesIO(image_data)).convert('RGB')
            img = np.array(pil_img)
        except Exception:
            img = None

    if img is None:
        return _add_without_cv('Could not analyze image automatically.')

    try:
        color_model = YOLO(str(color_cls_path))
        category_model = YOLO(str(category_cls_path))

        color_pred = color_model.predict(source=img, device='cpu')
        top1_color_idx = int(color_pred[0].probs.top1)
        predicted_color = color_model.names[top1_color_idx]

        category_pred = category_model.predict(source=img, device='cpu')
        top1_cat_idx = int(category_pred[0].probs.top1)
        category_conf = float(category_pred[0].probs.top1conf)
        raw_cloth_type = str(category_model.names[top1_cat_idx])
        selected_cloth_type = _format_predicted_cloth_type(raw_cloth_type)
    except Exception:
        return _add_without_cv('Could not analyze image automatically.')

    if category_conf < CATEGORY_CONFIDENCE_THRESHOLD:
        selected_cloth_type = None

    item_id = None
    if local_email:
        item_id = add_clothing_item(
            email=local_email,
            item_name=item_name,
            image_data=image_data,
        )

    category = _add_item_to_catalog(
        name=item_name,
        cloth_type=selected_cloth_type,
        image=image_data,
        color=predicted_color,
        item_id=item_id,
        conf=category_conf,
    )
    st.session_state.wardrobe_feedback = f'**Added 1 item to {category}.**'
    return True


def addclothemanual(
    item_name: str,
    selected_cloth_type: str | None,
    manual_color: str | None,
    local_email: str | None,
) -> bool:
    """Add a clothing item manually using name, type, and color."""
    if not selected_cloth_type or not manual_color:
        st.error('Please select clothe type and color.')
        return False

    item_id = None
    if local_email:
        item_id = add_clothing_item(
            email=local_email,
            item_name=item_name,
            cloth_type=selected_cloth_type,
            color=manual_color,
            wardrobe_category=CATEGORY_BY_CLOTH_TYPE.get(
                selected_cloth_type, 'Accessories ⌚'
            ),
        )

    category = _add_item_to_catalog(
        name=item_name,
        cloth_type=selected_cloth_type,
        color=manual_color,
        item_id=item_id,
    )
    st.session_state.wardrobe_feedback = (
        f'**Added {_plain_cloth_type_name(selected_cloth_type)} to {category}.**'
    )
    return True


@st.dialog('Edit wardrobe item')
def _edit_wardrobe_item(category, item_index, local_user):
    item = st.session_state.catalog[category][item_index]
    current_name = str(item.get('name', ''))
    current_color = item.get('color')
    current_cloth_type = item.get('cloth_type')
    has_image = bool(item.get('image'))
    item_id = item.get('id')

    with st.form(f'edit_item_{category}_{item_index}'):
        edited_name = st.text_input('Item name', value=current_name)
        if has_image:
            category_options = list(st.session_state.catalog.keys())
            edited_category = st.selectbox(
                'Category',
                category_options,
                index=category_options.index(category),
            )
            edited_cloth_type = current_cloth_type
            edited_color = current_color
            st.caption(
                'Image items keep their current image. You can rename or recategorise them.'
            )
        else:
            fallback_type = (
                current_cloth_type
                if current_cloth_type in CLOTH_TYPE_OPTIONS
                else CLOTH_TYPE_OPTIONS[0]
            )
            edited_cloth_type = st.selectbox(
                'Clothe type',
                CLOTH_TYPE_OPTIONS,
                index=CLOTH_TYPE_OPTIONS.index(fallback_type),
            )
            edited_category = CATEGORY_BY_CLOTH_TYPE.get(
                edited_cloth_type, 'Accessories ⌚'
            )
            edited_color = st.color_picker(
                'Color',
                value=current_color or '#94a3b8',
                width='stretch',
            )

        submitted = st.form_submit_button(
            'Save changes', type='primary', width='stretch'
        )

    if not submitted:
        return

    clean_name = edited_name.strip()
    if not clean_name:
        st.error('Item name is required.')
        return

    if local_user and item_id is not None:
        saved = update_clothing_item(
            email=local_user,
            clothing_id=int(item_id),
            item_name=clean_name,
            cloth_type=edited_cloth_type,
            color=edited_color,
            wardrobe_category=edited_category,
        )
        if not saved:
            st.error('Could not update this wardrobe item.')
            return

    _set_catalog_item(
        old_category=category,
        item_index=item_index,
        updated_item={
            'name': clean_name,
            'cloth_type': edited_cloth_type,
            'color': edited_color,
        },
        new_category=edited_category,
    )
    st.toast(f'Updated {clean_name}. ✅')
    st.rerun()


@st.dialog('Add a new clothe item')
def add_clothe_item():
    item_name = st.text_input(
        '**Clothe Item Name**',
        placeholder='Enter the item name',
        help='Example: White Office Shirt, Black Wide-Leg Pants',
    )

    uploaded_files = st.file_uploader(
        'Upload image(s) of the clothe item',
        type=['jpg', 'jpeg', 'png', 'bmp'],
        help='Supported formats: JPG, JPEG, PNG, BMP. Max file size: 10MB.',
        accept_multiple_files=False,
    )

    has_uploaded_files = bool(uploaded_files)
    selected_cloth_type = None
    manual_color = None

    if has_uploaded_files:
        file = uploaded_files
        st.image(file, caption=file.name)
        st.info('Image will be analysed with computer vision when you click Submit.')
    else:
        st.info('Upload an image, or enter the clothe details manually to continue.')

        selected_cloth_type = st.selectbox(
            '**Clothe Type**',
            CLOTH_TYPE_OPTIONS,
            index=None,
            placeholder='Select a clothe type',
            help='The wardrobe category will be assigned automatically from this type.',
        )

        manual_color = st.color_picker(
            '**Color**', help='Choose the color of the clothe item', width='stretch'
        )

    clean_item_name = item_name.strip()
    manual_entry_ready = (
        selected_cloth_type is not None
        and manual_color is not None
        and bool(clean_item_name)
    )
    upload_entry_ready = has_uploaded_files and bool(clean_item_name)

    if upload_entry_ready or manual_entry_ready:
        if st.button('Submit', type='primary', width='stretch'):
            local_email = st.session_state.get('local_user')

            added = False
            if has_uploaded_files:
                added = addclothemedia(uploaded_files, clean_item_name, local_email)
            else:
                added = addclothemanual(
                    clean_item_name,
                    selected_cloth_type,
                    manual_color,
                    local_email,
                )

            if added:
                st.rerun()


def _default_catalog():
    catalog = {category: [] for category in GUEST_DEFAULT_ITEMS}
    for category, items in GUEST_DEFAULT_ITEMS.items():
        for item in items:
            catalog[category].append(
                {
                    'name': item['name'],
                    'image': _load_guest_asset_bytes(item['asset']),
                    'color': None,
                    'cloth_type': item['cloth_type'],
                }
            )
    return catalog


def _catalog_has_any_items(catalog: dict) -> bool:
    if not isinstance(catalog, dict):
        return False
    return any(bool(items) for items in catalog.values())


# !!! Clothes catalogue !!!
local_user = st.session_state.get('local_user')
if 'catalog_owner' not in st.session_state:
    st.session_state.catalog_owner = None

catalog_missing = 'catalog' not in st.session_state
owner_changed = st.session_state.catalog_owner != local_user
guest_catalog_empty = local_user is None and (
    catalog_missing or not _catalog_has_any_items(st.session_state.get('catalog'))
)

if catalog_missing or owner_changed or guest_catalog_empty:
    if local_user:
        st.session_state.catalog = get_user_catalog(local_user)
    else:
        st.session_state.catalog = _default_catalog()
    st.session_state.catalog_owner = local_user

categories = list(st.session_state.catalog.keys())


# --- Top bar: Title + Action Buttons ---
st.markdown('<h1 class="wardrobe-title">👗 My Wardrobe</h1>', unsafe_allow_html=True)
st.divider()

feedback_message = st.session_state.pop('wardrobe_feedback', None)
if feedback_message:
    if feedback_message == 'Item deleted.':
        st.toast('**Item deleted**', icon='❌', duration='short')
    elif 'Added ' in feedback_message:
        st.toast(feedback_message, icon='✅', duration='short')
    else:
        st.success(feedback_message)

# --- Category Grid (2x2) ---
if st.session_state.selected_category is None:
    top_left, top_right = st.columns([3, 1])
    with top_left:
        wardrobe_search = st.text_input(
            'Search wardrobe',
            key='wardrobe_grid_search',
            placeholder='🔍 Search all items…',
            label_visibility='collapsed',
        )
    with top_right:
        if st.button(
            'Add Item',
            key='add_item_button',
            type='primary',
            width='stretch',
            icon='➕',
        ):
            add_clothe_item()

    if wardrobe_search.strip():
        q = wardrobe_search.strip().lower()
        matched = [
            {
                **(
                    item
                    if isinstance(item, dict)
                    else {
                        'name': item[0],
                        'image': item[1],
                        'color': None,
                        'cloth_type': None,
                    }
                ),
                '_category': cat,
            }
            for cat, entries in st.session_state.catalog.items()
            for item in entries
            if q
            in (item.get('name', '') if isinstance(item, dict) else item[0]).lower()
        ]
        if not matched:
            st.info('No items match your search.')
        else:
            num_cols = 3
            for i in range(0, len(matched), num_cols):
                cols = st.columns(num_cols, border=True)
                for j, col in enumerate(cols):
                    if i + j >= len(matched):
                        break
                    item = matched[i + j]
                    with col:
                        st.markdown(f'#### {item.get("name", "Unnamed")}')
                        if item.get('cloth_type'):
                            st.caption(item['cloth_type'])
                        st.caption(f'📁 {item["_category"]}')
                        img = item.get('image')
                        color = item.get('color')
                        if img:
                            st.image(img, width='content')
                        elif color:
                            st.markdown(
                                f"<div style='width:100%;height:140px;border-radius:0.75rem;background:{color};border:1px solid rgba(0,0,0,0.08);'></div>",
                                unsafe_allow_html=True,
                            )
    else:
        row1 = st.columns(2, border=True)
        row2 = st.columns(2, border=True)
        grid = [row1[0], row1[1], row2[0], row2[1]]

        for i, category in enumerate(categories):
            with grid[i]:
                st.markdown(f'### {category}')
                st.write(f'{len(st.session_state.catalog[category])} item(s)')
                if st.button(
                    f'Open {category}', key=f'cat_{category}', width='stretch'
                ):
                    st.session_state.selected_category = category
                    st.rerun()

# --- Clothing Grid ---
else:
    if st.button(
        '**Go Back**',
        key='back_button',
        type='primary',
        icon='⬅️',
    ):
        st.session_state.selected_category = None
        st.rerun()

    st.subheader(st.session_state.selected_category)
    items = st.session_state.catalog[st.session_state.selected_category]

    if not items:
        st.info('No items in this category yet. Use ➕ to add some!')
    else:
        cat_search = st.text_input(
            'Search category',
            key=f'wardrobe_cat_search_{st.session_state.selected_category}',
            placeholder='🔍 Search in this category…',
            label_visibility='collapsed',
        )
        if cat_search.strip():
            q = cat_search.strip().lower()
            display_items = [
                (orig_idx, item)
                for orig_idx, item in enumerate(items)
                if q
                in (item.get('name', '') if isinstance(item, dict) else item[0]).lower()
            ]
        else:
            display_items = list(enumerate(items))

        if not display_items:
            st.info('No items match your search.')
        else:
            num_cols = 3
            for row_start in range(0, len(display_items), num_cols):
                cols = st.columns(num_cols, border=True)
                for j, col in enumerate(cols):
                    if row_start + j >= len(display_items):
                        break
                    item_index, item = display_items[row_start + j]
                    if isinstance(item, dict):
                        name = item.get('name', 'Unnamed Item')
                        image = item.get('image')
                        if _is_stale_media_id(image):
                            image = None
                        color = item.get('color')
                        cloth_type = item.get('cloth_type')
                    else:
                        name, image = item
                        if _is_stale_media_id(image):
                            image = None
                        color = None
                        cloth_type = None

                    with col:
                        st.markdown(f'#### {name}')

                        if cloth_type:
                            st.caption(cloth_type)

                        if image:
                            st.image(image, width='content')
                        elif color:
                            st.markdown(
                                f"<div style='width: 100%; height: 180px; border-radius: 0.75rem; background: {color}; border: 1px solid rgba(0, 0, 0, 0.08);'></div>",
                                unsafe_allow_html=True,
                            )
                            st.caption(f'Color: {color}')

                        if st.button(
                            'Edit',
                            key=f'edit_{st.session_state.selected_category}_{item_index}',
                            type='secondary',
                            width='stretch',
                        ):
                            _edit_wardrobe_item(
                                st.session_state.selected_category,
                                item_index,
                                local_user,
                            )

                        def _delete_item(idx=item_index):
                            item_to_remove = st.session_state.catalog[
                                st.session_state.selected_category
                            ][idx]
                            item_id = (
                                item_to_remove.get('id')
                                if isinstance(item_to_remove, dict)
                                else None
                            )
                            if local_user and item_id is not None:
                                deleted = delete_clothing_item(local_user, int(item_id))
                                if not deleted:
                                    st.session_state.wardrobe_feedback = (
                                        'Could not delete item.'
                                    )
                                    st.rerun()
                                    return
                            st.session_state.catalog[
                                st.session_state.selected_category
                            ].pop(idx)
                            st.session_state.wardrobe_feedback = 'Item deleted.'
                            st.rerun()

                        delete_key = (
                            f'del_{st.session_state.selected_category}_{item_index}'
                        )
                        if st.button(
                            'Delete',
                            key=f'{delete_key}_fallback',
                            type='secondary',
                            icon='🗑️',
                            width='stretch',
                        ):
                            _delete_item()
