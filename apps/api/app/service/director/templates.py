from dataclasses import dataclass


@dataclass(frozen=True)
class ShotTemplate:
    id: str
    label_zh: str
    recommended_shot_scale: str
    subject_position: str
    start_action_template: str
    end_action_template: str
    crowd_action: str | None
    crowd_emotion: str | None
    camera_movement: str
    composition: str
    lens: str
    workflow_hint: str
    first_frame_fragments: tuple[str, ...]
    end_frame_fragments: tuple[str, ...]
    motion_fragments: tuple[str, ...]
    warnings: tuple[str, ...] = ()


SHOT_TEMPLATES: tuple[ShotTemplate, ...] = (
    ShotTemplate(
        id="enter_room_shock",
        label_zh="闯入震惊",
        recommended_shot_scale="medium_wide",
        subject_position="doorway foreground or room entrance foreground",
        start_action_template="{primary} pushes the door open and rushes into the room",
        end_action_template="{primary} stands inside the room facing everyone",
        crowd_action="everyone turns toward the entrance",
        crowd_emotion="shock",
        camera_movement="slow push-in",
        composition="primary subject at the doorway, meeting table and crowd visible",
        lens="28mm",
        workflow_hint="pose_control",
        first_frame_fragments=(
            "the primary subject is at the doorway or entrance foreground",
            "the meeting table and other people are visible",
            "not a seated business portrait",
        ),
        end_frame_fragments=(
            "the primary subject has entered the room",
            "the crowd is visibly shocked",
        ),
        motion_fragments=("the door opens, the subject enters, everyone turns in shock",),
        warnings=("POSE_CONTROL_RECOMMENDED", "SCENE_LAYOUT_CONFLICT_RISK"),
    ),
    ShotTemplate(
        id="door_open_reveal",
        label_zh="开门揭示",
        recommended_shot_scale="medium",
        subject_position="behind the opening door",
        start_action_template="the door begins to open",
        end_action_template="{primary} is revealed behind the open door",
        crowd_action="nearby people look toward the door",
        crowd_emotion="surprise",
        camera_movement="slow reveal push-in",
        composition="door frame creates a reveal composition",
        lens="35mm",
        workflow_hint="first_last_frame_video",
        first_frame_fragments=("door partially open, subject still partly hidden",),
        end_frame_fragments=("subject clearly revealed through the doorway",),
        motion_fragments=("the door opens and reveals the subject",),
    ),
    ShotTemplate(
        id="character_walks_forward",
        label_zh="人物逼近",
        recommended_shot_scale="medium",
        subject_position="center foreground",
        start_action_template="{primary} starts walking forward",
        end_action_template="{primary} approaches closer to camera",
        crowd_action=None,
        crowd_emotion=None,
        camera_movement="subtle backward tracking or push-in",
        composition="centered subject moving through depth",
        lens="35mm",
        workflow_hint="pose_control",
        first_frame_fragments=("full upper body visible, forward motion begins",),
        end_frame_fragments=("subject is closer and more dominant in frame",),
        motion_fragments=("the subject walks forward with controlled tension",),
        warnings=("POSE_CONTROL_RECOMMENDED",),
    ),
    ShotTemplate(
        id="character_turns_head",
        label_zh="人物转头",
        recommended_shot_scale="medium_closeup",
        subject_position="center frame",
        start_action_template="{primary} looks away from the camera direction",
        end_action_template="{primary} turns the head toward the source of tension",
        crowd_action=None,
        crowd_emotion=None,
        camera_movement="locked-off stable camera",
        composition="face and shoulder line clearly readable",
        lens="50mm",
        workflow_hint="portrait",
        first_frame_fragments=("head angled away, attention elsewhere",),
        end_frame_fragments=("head turned, eyes focused with tension",),
        motion_fragments=("a clear head turn and eye-line shift",),
    ),
    ShotTemplate(
        id="emotional_closeup",
        label_zh="情绪特写",
        recommended_shot_scale="closeup",
        subject_position="center close-up",
        start_action_template="{primary} holds back emotion",
        end_action_template="{primary} reveals a stronger emotional reaction",
        crowd_action=None,
        crowd_emotion=None,
        camera_movement="very slow push-in",
        composition="tight face close-up with shallow depth of field",
        lens="85mm",
        workflow_hint="portrait",
        first_frame_fragments=("tight facial detail, restrained emotion",),
        end_frame_fragments=("clear emotional transition in the eyes and face",),
        motion_fragments=("subtle facial expression change, stable identity",),
    ),
    ShotTemplate(
        id="two_person_confrontation",
        label_zh="双人对峙",
        recommended_shot_scale="medium",
        subject_position="foreground facing opponent",
        start_action_template="{primary} faces the opponent with restrained tension",
        end_action_template="{primary} confronts the opponent directly",
        crowd_action="the other person reacts defensively",
        crowd_emotion="tense",
        camera_movement="subtle handheld push-in",
        composition="two characters balanced in confrontation",
        lens="35mm",
        workflow_hint="dialogue",
        first_frame_fragments=("two-person blocking, visible tension",),
        end_frame_fragments=("direct confrontation, stronger emotional pressure",),
        motion_fragments=("the confrontation intensifies without jump cuts",),
    ),
    ShotTemplate(
        id="phone_reveal",
        label_zh="手机信息揭示",
        recommended_shot_scale="medium_closeup",
        subject_position="foreground with phone visible",
        start_action_template="{primary} looks down at the phone",
        end_action_template="{primary} reacts to the revealed message",
        crowd_action=None,
        crowd_emotion=None,
        camera_movement="slow push toward the phone and face",
        composition="phone screen and character reaction both readable",
        lens="50mm",
        workflow_hint="portrait",
        first_frame_fragments=("phone visible in foreground, face readable",),
        end_frame_fragments=("reaction to the information becomes clear",),
        motion_fragments=("attention shifts from phone to emotional reaction",),
    ),
    ShotTemplate(
        id="meeting_room_wide",
        label_zh="会议室全景",
        recommended_shot_scale="wide",
        subject_position="near the meeting table or doorway",
        start_action_template="the boardroom power dynamic is established",
        end_action_template="the power relation in the room becomes clear",
        crowd_action="people around the meeting table react to the focal subject",
        crowd_emotion="tense attention",
        camera_movement="slow push-in",
        composition="long meeting table, executives, doorway or focal subject visible",
        lens="24mm",
        workflow_hint="wide_scene",
        first_frame_fragments=("wide boardroom geography, readable table layout",),
        end_frame_fragments=("crowd and focal subject relation is clear",),
        motion_fragments=("subtle camera movement across the meeting room tension",),
        warnings=("SCENE_LAYOUT_CONFLICT_RISK",),
    ),
    ShotTemplate(
        id="authority_stands_up",
        label_zh="权威人物起身",
        recommended_shot_scale="medium_wide",
        subject_position="head of table or dominant foreground position",
        start_action_template="{primary} sits or stands with controlled authority",
        end_action_template="{primary} stands up and takes control of the room",
        crowd_action="others look toward the authority figure",
        crowd_emotion="pressure",
        camera_movement="low subtle push-in",
        composition="authority figure visually dominant over the room",
        lens="35mm",
        workflow_hint="pose_control",
        first_frame_fragments=("authority figure framed in a dominant position",),
        end_frame_fragments=("standing posture changes the power dynamic",),
        motion_fragments=("the authority figure rises, room attention shifts",),
        warnings=("POSE_CONTROL_RECOMMENDED",),
    ),
    ShotTemplate(
        id="crowd_reaction",
        label_zh="群众反应",
        recommended_shot_scale="medium_wide",
        subject_position="crowd distributed across the frame",
        start_action_template="the crowd notices the event",
        end_action_template="the crowd reacts visibly",
        crowd_action="multiple people turn, freeze, or exchange shocked looks",
        crowd_emotion="shock",
        camera_movement="quick controlled pan or stable wide shot",
        composition="several reactions visible in one frame",
        lens="28mm",
        workflow_hint="wide_scene",
        first_frame_fragments=("multiple people in frame before reaction peaks",),
        end_frame_fragments=("clear group reaction with readable faces",),
        motion_fragments=("the crowd reacts together, attention shifts across the room",),
    ),
    ShotTemplate(
        id="character_leaves",
        label_zh="人物离场",
        recommended_shot_scale="medium_wide",
        subject_position="moving toward exit or away from camera",
        start_action_template="{primary} turns away from the confrontation",
        end_action_template="{primary} leaves the scene decisively",
        crowd_action="others watch the departure",
        crowd_emotion="stunned silence",
        camera_movement="slow pull-out",
        composition="exit path visible, subject separated from the crowd",
        lens="35mm",
        workflow_hint="first_last_frame_video",
        first_frame_fragments=("subject begins to turn away",),
        end_frame_fragments=("subject exits, others remain behind",),
        motion_fragments=("a decisive exit with emotional distance",),
    ),
    ShotTemplate(
        id="establishing_scene",
        label_zh="场景建立镜头",
        recommended_shot_scale="wide",
        subject_position="no dominant human subject",
        start_action_template="the location is established",
        end_action_template="the atmosphere of the location becomes clear",
        crowd_action=None,
        crowd_emotion=None,
        camera_movement="slow atmospheric push-in",
        composition="clear geography and production design",
        lens="24mm",
        workflow_hint="wide_scene",
        first_frame_fragments=("wide establishing view of the scene",),
        end_frame_fragments=("the environment mood is emphasized",),
        motion_fragments=("subtle environmental motion, stable scene geography",),
    ),
)

TEMPLATE_BY_ID = {template.id: template for template in SHOT_TEMPLATES}
DEFAULT_TEMPLATE_ID = "meeting_room_wide"


def get_template(template_id: str | None) -> ShotTemplate:
    if template_id and template_id in TEMPLATE_BY_ID:
        return TEMPLATE_BY_ID[template_id]
    return TEMPLATE_BY_ID[DEFAULT_TEMPLATE_ID]


def all_template_ids() -> list[str]:
    return [template.id for template in SHOT_TEMPLATES]
