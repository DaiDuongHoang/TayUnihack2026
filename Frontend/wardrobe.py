import streamlit as st
import os
from pathlib import Path
from Authentication import is_authenticated, login_screen
from data_backend import (
    add_clothing_item,
    delete_clothing_item,
    get_user_catalog,
    update_clothing_item,
)

danger_delete_button = None


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

if not is_authenticated():
    login_screen(
        title='Sign in to access your wardrobe',
        description='Use Google or your local email/password account to continue.',
    )
    st.stop()

# CSS animations
st.html("""
<style>
/* Slide-fade-DOWN keyframe */
@keyframes slideFadeDown {
    from {
        opacity: 0;
        transform: translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Apply to all buttons */
div[data-testid="stButton"] button {
    animation: slideFadeDown 0.65s cubic-bezier(0.34, 1.56, 0.64, 1) both;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

/* Apply to bordered column/grid boxes */
div[data-testid="stColumn"] {
    animation: slideFadeDown 0.65s cubic-bezier(0.34, 1.56, 0.64, 1) both;
    transition: transform 0.28s ease, box-shadow 0.28s ease;
}

div[data-testid="stColumn"]:hover {
    transform: translateY(-10px) scale(1.01);
    box-shadow: 0 22px 48px rgba(0, 0, 0, 0.20);
}

/* Apply to horizontal divider */
div[data-testid="stDivider"] {
    animation: slideFadeDown 0.65s cubic-bezier(0.34, 1.56, 0.64, 1) 0.3s both;
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

/* Keep hover effect on buttons */
div[data-testid="stButton"] button:hover {
    transform: translateY(-5px) scale(1.11);
    box-shadow: 0px 18px 36px rgba(0, 0, 0, 0.36);
}

/* Dedicated animation for the Go Back button */
@keyframes backButtonFloat {
    0%,
    100% {
        transform: translateY(0);
    }
    50% {
        transform: translateY(-7px);
    }
}

@keyframes backButtonWiggle {
    0% {
        transform: translateX(-6px) scale(1.09) rotate(0deg);
    }
    25% {
        transform: translateX(-10px) scale(1.11) rotate(-2deg);
    }
    50% {
        transform: translateX(-6px) scale(1.12) rotate(2deg);
    }
    75% {
        transform: translateX(-10px) scale(1.11) rotate(-1deg);
    }
    100% {
        transform: translateX(-6px) scale(1.09) rotate(0deg);
    }
}

.st-key-back_button button {
    animation: backButtonFloat 1.8s ease-in-out infinite;
    border: 1px solid rgba(59, 130, 246, 0.35);
    transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
}

.st-key-back_button button:hover {
    animation: backButtonWiggle 0.45s ease-in-out infinite;
    box-shadow: 0 14px 30px rgba(59, 130, 246, 0.55);
    filter: brightness(1.14) saturate(1.2);
}

/* Apply slideFadeDown animation to st.success (alert elements) */
/* Delete button — danger pulse idle + shake on hover */
@keyframes deleteDangerPulse {
    0%, 100% {
        box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.0);
        border-color: rgba(239, 68, 68, 0.28);
    }
    50% {
        box-shadow: 0 0 0 7px rgba(239, 68, 68, 0.18);
        border-color: rgba(239, 68, 68, 0.65);
    }
}

@keyframes deleteShake {
    0%   { transform: translateX(0) scale(1.04); }
    25%  { transform: translateX(-2px) scale(1.05); }
    50%  { transform: translateX(2px) scale(1.06); }
    75%  { transform: translateX(-1px) scale(1.05); }
    100% { transform: translateX(0) scale(1.04); }
}

[class*="st-key-del"] button {
    animation: slideFadeDown 0.65s cubic-bezier(0.34, 1.56, 0.64, 1) both,
               deleteDangerPulse 2.0s ease-in-out 0.7s infinite !important;
    border: 1.5px solid rgba(239, 68, 68, 0.32) !important;
    color: #dc2626 !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease,
                background 0.18s ease, border-color 0.18s ease !important;
}

[class*="st-key-del"] button:hover {
    animation: deleteShake 0.42s ease-in-out infinite !important;
    box-shadow: 0 14px 34px rgba(239, 68, 68, 0.55) !important;
    background: rgba(254, 226, 226, 0.88) !important;
    border-color: rgba(239, 68, 68, 0.75) !important;
    color: #b91c1c !important;
}

/* Apply slideFadeDown animation to st.success (alert elements) */
div[data-testid="stAlert"] {
    animation: slideFadeDown 0.65s cubic-bezier(0.34, 1.56, 0.64, 1) both;
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

div[data-testid="stAlert"]:hover {
    transform: translateY(-6px);
    box-shadow: 0 14px 32px rgba(0, 0, 0, 0.14);
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
            'cloth_type': '🧥 Jacket',
        },
        {
            'name': 'Trench Coat',
            'asset': 'Trench coat.png',
            'cloth_type': '🥼 Coat',
        },
        {
            'name': 'Puffer Vest',
            'asset': 'puffer vest.png',
            'cloth_type': '🧥 Jacket',
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


def _add_item_to_catalog(name, cloth_type, image=None, color=None, item_id=None):
    _ensure_catalog_categories()
    category = CATEGORY_BY_CLOTH_TYPE.get(cloth_type, 'Accessories ⌚')
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
        try:
            from ultralytics import YOLO
        except ModuleNotFoundError:
            st.error(
                'Image auto-detection is unavailable because ultralytics is not installed.'
            )
            st.info('Please remove the upload and enter details manually for now.')
            return

        current_path = os.path.dirname(__file__)
        parent_path = os.path.dirname(current_path)
        color_cls_path = os.path.join(parent_path, 'models', 'best_color_cls.pt')
        category_cls_path = os.path.join(parent_path, 'models', 'best_category_cls.pt')

        if not os.path.exists(color_cls_path) or not os.path.exists(category_cls_path):
            st.error('Model files are missing. Please check the models folder.')
            return

        color_model = YOLO(str(color_cls_path))
        category_model = YOLO(str(category_cls_path))

        file = uploaded_files
        st.image(file, caption=file.name)
        pred = color_model.predict(source=file)
        clothe_color = pred[0]
        top_1_idx = int(clothe_color.probs.top1)
        manual_color = color_model.names[top_1_idx]

        pred = category_model.predict(source=file)
        clothe_category = pred[0]
        top_1_idx = int(clothe_category.probs.top1)
        selected_cloth_type = category_model.names[top_1_idx]

        st.success('Successfully uploaded 1 file!')
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

            if has_uploaded_files:
                file = uploaded_files
                image_data = file.getvalue()
                item_id = None

                if local_email:
                    item_id = add_clothing_item(
                        email=local_email,
                        item_name=clean_item_name,
                        image_data=image_data,
                    )

                category = _add_item_to_catalog(
                    name=clean_item_name,
                    cloth_type=selected_cloth_type,
                    image=image_data,
                    item_id=item_id,
                )
                st.session_state.wardrobe_feedback = f'**Added 1 item to {category}.**'
            else:
                item_id = None
                if local_email:
                    item_id = add_clothing_item(
                        email=local_email,
                        item_name=clean_item_name,
                        cloth_type=selected_cloth_type,
                        color=manual_color,
                        wardrobe_category=CATEGORY_BY_CLOTH_TYPE.get(
                            selected_cloth_type, 'Accessories ⌚'
                        ),
                    )
                category = _add_item_to_catalog(
                    name=clean_item_name,
                    cloth_type=selected_cloth_type,
                    color=manual_color,
                    item_id=item_id,
                )
                st.session_state.wardrobe_feedback = f'**Added {_plain_cloth_type_name(selected_cloth_type)} to {category}.**'

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
st.title('👗 My Wardrobe')
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
    if st.button(
        'Add Item',
        key='add_item_button',
        type='primary',
        width='stretch',
        icon='➕',
    ):
        add_clothe_item()

    row1 = st.columns(2, border=True)
    row2 = st.columns(2, border=True)
    grid = [row1[0], row1[1], row2[0], row2[1]]

    for i, category in enumerate(categories):
        with grid[i]:
            st.markdown(f'### {category}')
            st.write(f'{len(st.session_state.catalog[category])} item(s)')
            if st.button(f'Open {category}', key=f'cat_{category}', width='stretch'):
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
        num_cols = 3
        for i in range(0, len(items), num_cols):
            cols = st.columns(num_cols, border=True)
            for j, col in enumerate(cols):
                if i + j < len(items):
                    item = items[i + j]
                    if isinstance(item, dict):
                        name = item.get('name', 'Unnamed Item')
                        image = item.get('image')
                        color = item.get('color')
                        cloth_type = item.get('cloth_type')
                    else:
                        name, image = item
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

                        item_index = i + j

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
                        if danger_delete_button is not None:
                            danger_delete_button(
                                key=delete_key,
                                data={
                                    'start': 'Hold to Delete',
                                    'continue': 'Keep holding...',
                                    'completed': 'Deleted',
                                },
                                on_confirmed_change=_delete_item,
                                width='content',
                            )
                        else:
                            if st.button(
                                'Delete',
                                key=f'{delete_key}_fallback',
                                type='secondary',
                                icon='🗑️',
                                width='stretch',
                            ):
                                _delete_item()
