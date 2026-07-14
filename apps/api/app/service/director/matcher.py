from app.infrastructure.models.shot import ShotRecord
from app.service.director.templates import DEFAULT_TEMPLATE_ID, TEMPLATE_BY_ID

KEYWORDS_BY_TEMPLATE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("enter_room_shock", ("冲进", "闯入", "推门", "进门", "rushes in", "bursts in")),
    ("door_open_reveal", ("开门", "门打开", "reveal", "door opens")),
    ("character_walks_forward", ("走向", "逼近", "上前", "walks forward", "approaches")),
    ("character_turns_head", ("转头", "回头", "看向", "turns head", "looks back")),
    ("emotional_closeup", ("特写", "流泪", "崩溃", "隐忍", "closeup", "close-up")),
    ("two_person_confrontation", ("对峙", "质问", "争吵", "confront", "argument")),
    ("phone_reveal", ("手机", "信息", "短信", "来电", "phone", "message")),
    ("meeting_room_wide", ("会议室", "董事会", "会议桌", "boardroom", "meeting room")),
    ("authority_stands_up", ("站起", "起身", "发话", "stands up")),
    ("crowd_reaction", ("震惊", "哗然", "众人", "everyone", "crowd", "shock")),
    ("character_leaves", ("离开", "转身离去", "走出", "leaves")),
    ("establishing_scene", ("环境", "空镜", "建筑", "外景", "establishing")),
)


def recommend_template_id(shot: ShotRecord) -> str:
    for value in (shot.action_summary, shot.visual_description, shot.story_description, shot.name):
        text = normalize(value)
        if not text:
            continue
        for template_id, keywords in KEYWORDS_BY_TEMPLATE:
            if any(keyword.lower() in text for keyword in keywords):
                return template_id
    return DEFAULT_TEMPLATE_ID


def valid_template_id(template_id: str | None) -> bool:
    return template_id in TEMPLATE_BY_ID if template_id else False


def normalize(value: str | None) -> str:
    return " ".join(value.strip().lower().split()) if value else ""
