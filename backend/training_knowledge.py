"""
Training Knowledge Base for RAG-based AI Training Assistant.
All content represents general operator training guidance for excavator operation.
This is NOT official CAT documentation. Citations will clearly indicate this.
"""
from __future__ import annotations

KNOWLEDGE: list[dict] = [
    # ── HYDRAULIC SYSTEM ──────────────────────────────────────────────────────
    {
        "id": "hyd_temp_001",
        "title": "Hydraulic System — Temperature Monitoring",
        "section": "Hydraulic Temperature",
        "tags": ["hydraulic", "temperature", "warning", "overheating", "hyd_temp"],
        "content": (
            "High hydraulic temperature is one of the most common issues operators encounter. "
            "It typically results from extended high-load operation without rest cycles, "
            "operating with a low hydraulic oil level, a clogged hydraulic filter, or a "
            "malfunctioning cooling fan. In hot ambient conditions, the hydraulic system "
            "works harder to maintain pressure. If the temperature warning light activates, "
            "reduce hydraulic demand immediately by lowering engine RPM, completing the "
            "current cycle slowly, then idling for several minutes to allow cooling. "
            "Do not shut down immediately under high temperature — allow idle cooling first."
        ),
    },
    {
        "id": "hyd_temp_002",
        "title": "Hydraulic System — High Temperature Response",
        "section": "Hydraulic Temperature — Operator Actions",
        "tags": ["hydraulic", "temperature", "response", "action", "overheating"],
        "content": (
            "When hydraulic temperature exceeds normal operating range: "
            "1) Reduce work intensity — avoid simultaneous multi-function operation. "
            "2) Check hydraulic oil level if safe to do so. "
            "3) Inspect that the cooling fins and radiator are not blocked by debris. "
            "4) Reduce ambient heat exposure if possible. "
            "5) Allow the machine to idle with the boom slightly raised for 3–5 minutes. "
            "6) If temperature does not return to normal range, park safely and notify maintenance. "
            "Never operate a machine with a confirmed hydraulic system fault — this can cause "
            "sudden loss of steering, boom, or travel control."
        ),
    },
    {
        "id": "hyd_basics_001",
        "title": "Hydraulic System — Fundamentals",
        "section": "Basic Hydraulic Operation",
        "tags": ["hydraulic", "fundamentals", "pressure", "pump", "oil"],
        "content": (
            "The hydraulic system powers the excavator's boom, arm, bucket, swing, and travel. "
            "A hydraulic pump driven by the engine converts mechanical energy into hydraulic pressure. "
            "This pressurised oil flows through control valves to hydraulic cylinders and motors. "
            "The main pump output pressure typically ranges from 300–350 bar at full load. "
            "Key indicators to watch: hydraulic oil temperature gauge, hydraulic oil level sight glass, "
            "and the hydraulic filter restriction indicator. Always maintain hydraulic oil at the "
            "correct level — low oil causes pump cavitation, leading to pump failure."
        ),
    },

    # ── ENGINE & RPM ──────────────────────────────────────────────────────────
    {
        "id": "engine_rpm_001",
        "title": "Engine — RPM and Load Management",
        "section": "Engine Operation",
        "tags": ["engine", "rpm", "power", "load", "throttle"],
        "content": (
            "The engine RPM should be set according to workload. Most excavators have "
            "selectable power modes: Economy (eco), Standard, and Power. "
            "Economy mode reduces RPM and fuel consumption by 15–25% during light work. "
            "Use Power mode only for heavy digging or tramming uphill. "
            "Abnormal RPM behaviour — such as RPM dropping under light load or hunting (fluctuating) "
            "— can indicate a fuel system issue, a dirty air filter, or a fault in the engine "
            "management system. Log and report unusual RPM behaviour to maintenance."
        ),
    },
    {
        "id": "engine_rpm_002",
        "title": "Engine — Auto-idle and Shutdown",
        "section": "Idle Management",
        "tags": ["engine", "auto-idle", "idle", "fuel", "shutdown", "idle_reduction"],
        "content": (
            "Auto-idle automatically reduces engine RPM when no operator input is detected "
            "for a set period (typically 4–8 seconds). This reduces fuel consumption during "
            "short waiting periods. Auto-shutdown turns the engine off after extended idle "
            "(typically 5 minutes). Always use auto-idle when waiting for trucks, during "
            "signals, or when briefly leaving the cab. Disabling auto-idle wastes fuel "
            "and increases maintenance costs. If the auto-idle feature is not functioning, "
            "manually reduce throttle to low idle when not actively working."
        ),
    },

    # ── IDLE TIME ─────────────────────────────────────────────────────────────
    {
        "id": "idle_001",
        "title": "Idle Time — Causes and Reduction",
        "section": "Idle Time Management",
        "tags": ["idle", "idle_time", "fuel", "productivity", "idle_reduction", "excess_idle"],
        "content": (
            "Excessive idle time is one of the largest sources of fuel waste on a construction site. "
            "Common causes include: waiting for trucks to be spotted, waiting for ground crew clearance, "
            "end-of-task delays before the next task begins, operator breaks with engine running, "
            "and signal/communication delays between operators and ground crew. "
            "Every 10 minutes of unnecessary idle consumes approximately 1–3 litres of fuel "
            "depending on engine size, with no productive output. "
            "Target: keep idle time below 20% of total shift time."
        ),
    },
    {
        "id": "idle_002",
        "title": "Idle Time — Reduction Strategies",
        "section": "Idle Time Management — Operator Actions",
        "tags": ["idle", "idle_reduction", "strategy", "coordination", "fuel"],
        "content": (
            "To reduce idle time: "
            "1) Communicate with truck spotters — if a delay is longer than 2 minutes, lower "
            "the boom to the ground and reduce RPM to low idle. "
            "2) Enable auto-idle and auto-shutdown features. "
            "3) Pre-plan the digging face — reposition before the next truck arrives so digging "
            "starts immediately when the truck is spotted. "
            "4) Coordinate with site supervisor if delays are systematic (truck cycle time mismatch). "
            "5) Use the engine hours meter to track cumulative idle vs. working hours."
        ),
    },

    # ── CYCLE TIME ────────────────────────────────────────────────────────────
    {
        "id": "cycle_001",
        "title": "Cycle Time — Understanding and Optimization",
        "section": "Excavation Cycle Time",
        "tags": ["cycle_time", "productivity", "excavation", "swing", "optimization"],
        "content": (
            "A complete excavation cycle consists of: dig (filling the bucket), swing loaded "
            "(swinging to the truck), dump (releasing material into the truck body), and swing empty "
            "(returning to the dig face). Typical cycle times range from 20–35 seconds depending on "
            "swing angle, material type, and operator technique. "
            "Key factors affecting cycle time: swing angle (minimise to under 90 degrees where possible), "
            "bench height (dig at optimal reach rather than over-extending), bucket fill factor "
            "(aim for 85–100% fill per pass), and smooth blending of movements to avoid hesitation."
        ),
    },
    {
        "id": "cycle_002",
        "title": "Cycle Time — Technique Improvements",
        "section": "Excavation Technique",
        "tags": ["cycle_time", "technique", "swing", "bucket", "payload", "productivity"],
        "content": (
            "To improve excavation cycle times: "
            "1) Position the machine so the swing angle to the truck is minimised — ideally under 45 degrees. "
            "2) Begin the swing as soon as the bucket clears the bench — do not wait until the arm is fully retracted. "
            "3) Control dump height — swing the boom down smoothly during the swing loaded phase so dumping "
            "is completed at the correct height without over-raising. "
            "4) Return the arm to dig position during the swing empty phase. "
            "5) Avoid over-digging past the machine's optimal reach — reposition the machine instead. "
            "6) Match bucket size to material type — heavy, wet material may require underfilling."
        ),
    },

    # ── BLIND ZONES & SAFETY ──────────────────────────────────────────────────
    {
        "id": "blind_zone_001",
        "title": "Blind Zones — Machine Awareness",
        "section": "Blind Zone Management",
        "tags": ["blind_zone", "safety", "proximity", "personnel", "awareness", "person_close"],
        "content": (
            "Every excavator has defined blind zones — areas around the machine where the operator "
            "cannot see directly from the cab, even with mirrors and cameras. "
            "Typical blind zones exist: directly behind the counterweight (the largest), "
            "close to the tracks on both sides at ground level, and directly under the boom "
            "when it is raised high. The rear blind zone on a standard excavator can extend "
            "5–8 metres. Ground workers must never enter these zones without radio communication "
            "with the operator. Cameras and proximity sensors supplement but do not replace "
            "proper exclusion zone management."
        ),
    },
    {
        "id": "blind_zone_002",
        "title": "Blind Zones — Exclusion Zone Management",
        "section": "Personnel Safety",
        "tags": ["blind_zone", "exclusion_zone", "safety", "personnel", "proximity", "ttc_low"],
        "content": (
            "Exclusion zone management is a critical safety practice: "
            "1) Establish a physical exclusion zone around the machine — typically a minimum of 5 metres. "
            "2) All ground workers must be briefed on the exclusion zone boundaries before work begins. "
            "3) Stop all machine movement immediately if an unauthorised person enters the exclusion zone. "
            "4) Use a spotter when reversing or tramming in congested areas. "
            "5) Conduct a 360-degree walk-around before starting the machine. "
            "6) Use travel alarm, horn, and rotating beacon to warn ground workers of machine movement. "
            "If a proximity warning activates during operation, stop movement and locate the person "
            "before resuming."
        ),
    },

    # ── PRE-OPERATION ─────────────────────────────────────────────────────────
    {
        "id": "pre_op_001",
        "title": "Pre-operation Inspection — Walk-around",
        "section": "Pre-operation Safety",
        "tags": ["pre_operation", "inspection", "walkaround", "safety", "seatbelt"],
        "content": (
            "The pre-operation walk-around is mandatory before every shift. Check: "
            "1) Under the machine for fluid leaks (oil, coolant, hydraulic fluid). "
            "2) Tracks and undercarriage — loose track shoes, damaged rollers, worn sprockets. "
            "3) Boom, arm and bucket — cracks, worn pins, loose bolts, bucket tooth condition. "
            "4) Mirrors and cameras — clean and properly aligned. "
            "5) Lights, horn, and travel alarm — functional. "
            "6) All access ladders and handholds — secure. "
            "Document any faults before starting. Never operate a machine with a known "
            "safety-critical defect — park and tag out until maintenance clears it."
        ),
    },
    {
        "id": "pre_op_002",
        "title": "Pre-operation — Cab Checks",
        "section": "Cab Checks",
        "tags": ["pre_operation", "seatbelt", "cab", "controls", "safety"],
        "content": (
            "Cab checks before starting: "
            "1) Seatbelt — must latch securely and retract smoothly. Never operate without seatbelt fastened. "
            "2) Seat adjustment — position so all controls are within comfortable reach. "
            "3) Mirrors — adjust rear-view mirrors before moving. "
            "4) Emergency stop — know its location. "
            "5) All warning lights — confirm none are illuminated at startup (except ones that clear during self-test). "
            "6) Joystick pattern — confirm your control pattern (ISO or SAE) is set correctly. "
            "The seatbelt is not optional — it is the primary operator protection in a tip-over event."
        ),
    },

    # ── WET GROUND OPERATION ──────────────────────────────────────────────────
    {
        "id": "wet_ground_001",
        "title": "Wet Ground — Safe Operation",
        "section": "Wet Ground Operation",
        "tags": ["wet_ground", "rain", "stability", "slope", "speed", "weather"],
        "content": (
            "Operating on wet or soft ground significantly increases risks of machine instability, "
            "track slip, and tip-overs. Key rules: "
            "1) Reduce travel speed — the machine's centre of gravity shifts more easily on soft ground. "
            "2) Avoid turning sharply or making sudden directional changes. "
            "3) Keep the bucket low and close to the machine during tramming. "
            "4) Increase the safety distance from bench edges and embankments — wet ground is "
            "weaker and can collapse without warning. "
            "5) Avoid parking on slopes in wet conditions. "
            "6) Be aware that tracks can lose traction suddenly on wet clay or smooth rock."
        ),
    },
    {
        "id": "wet_ground_002",
        "title": "Wet Ground — Slope Stability",
        "section": "Wet Ground — Slope Work",
        "tags": ["wet_ground", "slope", "stability", "safety", "rain", "terrain"],
        "content": (
            "When working on slopes in wet conditions: "
            "1) Always position the machine so it faces uphill when possible — this is the most stable orientation. "
            "2) The maximum recommended side-slope angle for excavators is typically 15–25 degrees "
            "(check the specific machine's stability chart). Wet conditions reduce this safe limit. "
            "3) If the machine begins to slide, lower the bucket to the ground immediately — "
            "it acts as an anchor. Do not attempt to swing or tram while sliding. "
            "4) Avoid digging from the downhill side of a bench in wet conditions. "
            "5) After heavy rain, wait for ground assessment before resuming slope work."
        ),
    },

    # ── EXCAVATION TECHNIQUE ──────────────────────────────────────────────────
    {
        "id": "excavation_001",
        "title": "Excavation — Basic Technique",
        "section": "Excavation Fundamentals",
        "tags": ["excavation", "digging", "technique", "bucket", "arm", "productivity"],
        "content": (
            "Proper excavation technique: "
            "1) Set the boom so the arm is approximately perpendicular to the ground at the start of the dig. "
            "2) Curl the bucket before driving the arm in — this maximises penetration force. "
            "3) Use the arm to pull material towards the machine; use the bucket curl to load the bucket. "
            "4) Fill the bucket in 2–3 passes for loose material, more for hard material. "
            "5) Avoid relying on the boom down force to load the bucket — use arm crowd and bucket curl. "
            "6) For hard material, use short 'chipping' motions rather than one full stroke."
        ),
    },
    {
        "id": "excavation_002",
        "title": "Excavation — Loading Trucks",
        "section": "Truck Loading",
        "tags": ["excavation", "truck", "loading", "payload", "positioning"],
        "content": (
            "For efficient and safe truck loading: "
            "1) Position the excavator so the loaded swing angle to the truck is minimised. "
            "2) Never swing over the truck cab — always swing over the truck bed. "
            "3) Signal the truck driver when it is safe to position. "
            "4) Aim for consistent passes — aim for 3–4 passes to fill a standard truck body. "
            "5) Place material towards the front of the truck bed first to keep the load balanced. "
            "6) Avoid dropping material from excessive height — this damages the truck body and "
            "wastes material that bounces out. "
            "7) Signal the driver clearly when loading is complete before they pull away."
        ),
    },

    # ── TRENCHING & GRADING ───────────────────────────────────────────────────
    {
        "id": "trenching_001",
        "title": "Trenching — Technique and Safety",
        "section": "Trenching",
        "tags": ["trenching", "excavation", "technique", "safety", "stability"],
        "content": (
            "Trenching requires careful attention to spoil placement and trench wall stability: "
            "1) Place spoil at least 600mm from the trench edge to reduce surcharge load on walls. "
            "2) Never enter a trench without shoring or battering if it is deeper than regulations permit. "
            "3) Work from one end of the trench, moving in one direction. "
            "4) Keep the machine tracks parallel to the trench direction for stability. "
            "5) If trench walls begin to crack or lean, stop immediately, park the machine safely, "
            "and report to the site supervisor. "
            "6) In wet conditions, trench walls are significantly weaker — increase monitoring frequency."
        ),
    },
    {
        "id": "grading_001",
        "title": "Grading — Technique",
        "section": "Grading and Finishing",
        "tags": ["grading", "technique", "bucket", "finish", "slope"],
        "content": (
            "Using an excavator for grading and finishing: "
            "1) Use the back of the bucket (bucket curl fully open) as a blade to grade material. "
            "2) Work from higher to lower elevation for best control. "
            "3) Lower the boom slowly and smoothly — use feathered inputs, not jerky movements. "
            "4) A tilt bucket significantly improves grading accuracy for sloped surfaces. "
            "5) Check finished grade with a level or laser frequently. "
            "6) Avoid over-grading — take thin passes and check frequently rather than removing "
            "too much material."
        ),
    },

    # ── PAYLOAD AWARENESS ─────────────────────────────────────────────────────
    {
        "id": "payload_001",
        "title": "Payload — Awareness and Management",
        "section": "Payload Management",
        "tags": ["payload", "truck", "overload", "productivity", "tare"],
        "content": (
            "Payload awareness is critical for both productivity and equipment safety: "
            "1) Know the rated payload of the trucks being loaded — overloading causes tyre damage, "
            "suspension damage, and regulatory penalties. "
            "2) Modern excavators with payload monitoring systems display bucket weight on the screen — "
            "use this to target consistent fills. "
            "3) Material density varies widely — wet clay is much heavier than dry sand. "
            "Adjust fill factor accordingly. "
            "4) Under-filling trucks also reduces productivity — aim for the rated payload. "
            "5) A consistent fill pattern produces more predictable truck payload results than "
            "irregular digging."
        ),
    },

    # ── FUEL EFFICIENCY ───────────────────────────────────────────────────────
    {
        "id": "fuel_001",
        "title": "Fuel Efficiency — Operator Practices",
        "section": "Fuel-efficient Operation",
        "tags": ["fuel", "efficiency", "idle", "rpm", "economy", "idle_reduction"],
        "content": (
            "Key fuel saving practices for excavator operators: "
            "1) Use economy mode during light or medium work — saves 15–25% fuel. "
            "2) Enable auto-idle to reduce RPM when not actively digging. "
            "3) Minimise idle time — every 10 minutes of unnecessary idle wastes fuel. "
            "4) Smooth, coordinated movements use less fuel than jerky, multi-axis inputs. "
            "5) Dig at the optimal reach rather than over-extending — over-extended cylinders "
            "require higher pump pressure. "
            "6) Match engine power mode to task — do not use full power for light positioning work. "
            "7) Monitor the fuel gauge and report unusually high consumption to maintenance "
            "(can indicate a fuel leak or injector issue)."
        ),
    },

    # ── SAFETY — GENERAL ─────────────────────────────────────────────────────
    {
        "id": "safety_001",
        "title": "Safety — General Principles",
        "section": "General Safety",
        "tags": ["safety", "general", "risk", "hazard", "procedure"],
        "content": (
            "General safety principles for excavator operators: "
            "1) Never operate a machine you are not authorised and trained for. "
            "2) Conduct a pre-operation inspection every shift without exception. "
            "3) Know your machine's rated capacities — do not lift loads beyond the rated lifting capacity. "
            "4) Communicate clearly with ground crew before any movement. "
            "5) Stop work and investigate any unusual sound, smell, vibration, or warning indicator. "
            "6) Safety systems (proximity warnings, tilt alarms) must not be bypassed or ignored. "
            "7) In any doubt about safety of a situation — stop. It is always correct to pause and assess."
        ),
    },
    {
        "id": "safety_002",
        "title": "Safety — Emergency Procedures",
        "section": "Emergency Response",
        "tags": ["safety", "emergency", "evacuation", "rollover", "fire"],
        "content": (
            "Emergency procedures: "
            "Tip-over: Do not jump — brace yourself and hold the handholds. The ROPS (rollover protection) "
            "is designed to protect you if you remain seated and belted. "
            "Fire: Activate the fire suppression system if fitted. Exit the machine safely — "
            "use the emergency exit if the main door is blocked. Move upwind and away from the machine. "
            "Contact emergency services immediately. "
            "Loss of hydraulic control: Lower the attachment to the ground using gravity if possible. "
            "Engage the travel lock. Shut down the engine if safe. "
            "Person struck or near-miss: Stop all movement immediately. "
            "Call for emergency assistance. Do not move the machine until investigators clear it."
        ),
    },

    # ── SWING OPERATION ───────────────────────────────────────────────────────
    {
        "id": "swing_001",
        "title": "Swing — Safe and Efficient Operation",
        "section": "Swing Operation",
        "tags": ["swing", "rotation", "cycle_time", "safety", "blind_zone"],
        "content": (
            "The swing (slew) function rotates the upper structure and is central to excavator productivity. "
            "Safe swing practices: "
            "1) Always check that the swing path is clear before slewing. "
            "2) Never swing over the cab of a truck or nearby personnel. "
            "3) The counterweight swings in the opposite direction to the boom — be aware of "
            "the rear counterweight's swept path. "
            "4) For efficiency, begin slewing as soon as the bucket clears the material. "
            "5) Control swing speed — excessive swing speed causes material spill and puts "
            "stress on the swing motor and ring gear. "
            "6) Feather the swing deceleration — do not let the machine jerk to a stop."
        ),
    },

    # ── MACHINE COMPONENTS ────────────────────────────────────────────────────
    {
        "id": "components_001",
        "title": "Machine Components — Overview",
        "section": "Machine Overview",
        "tags": ["components", "overview", "boom", "arm", "bucket", "undercarriage", "cabin"],
        "content": (
            "Key excavator components: "
            "Upper structure: cab, engine compartment, hydraulic system, swing mechanism, counterweight. "
            "Attachment: boom (main arm structure), arm (also called stick), bucket (digging tool). "
            "Undercarriage: tracks, rollers, idlers, sprockets, track frame. "
            "The upper structure rotates 360 degrees on the undercarriage via the swing ring and motor. "
            "The counterweight at the rear balances the attachment weight during lifting operations. "
            "Hydraulic cylinders control boom, arm, and bucket angles. The travel motors drive the tracks."
        ),
    },
    {
        "id": "components_002",
        "title": "Machine Components — Undercarriage",
        "section": "Tracks and Undercarriage",
        "tags": ["undercarriage", "tracks", "rollers", "sprockets", "maintenance"],
        "content": (
            "The undercarriage is the highest-wear component on an excavator. "
            "Key undercarriage components: "
            "Track shoes — provide traction, available in different widths for different ground conditions. "
            "Carrier rollers — support the top of the track chain. "
            "Track rollers — support the bottom of the track chain under the frame. "
            "Front idler — guides the track at the front. "
            "Sprocket — drives the track chain from the travel motor. "
            "Regular inspection: check track tension (should have correct sag), look for worn "
            "or cracked track shoes, and listen for knocking sounds indicating worn rollers."
        ),
    },

    # ── TROUBLESHOOTING ───────────────────────────────────────────────────────
    {
        "id": "trouble_001",
        "title": "Troubleshooting — Slow Excavation Cycles",
        "section": "Troubleshooting",
        "tags": ["troubleshooting", "slow", "cycle_time", "hydraulic", "power", "productivity"],
        "content": (
            "If excavation cycles are slower than normal, common causes include: "
            "1) Engine not at correct RPM — check throttle setting and power mode. "
            "2) High hydraulic oil temperature — hydraulic system is in thermal protection mode. "
            "3) Low hydraulic oil level — reduces pump output. "
            "4) Hydraulic filter restriction — restricts flow. "
            "5) Worn bucket teeth — increases digging resistance. "
            "6) Operator technique — over-extending reach, trying to take too large a cut per pass. "
            "7) Ground conditions — hard or frozen material requires smaller cuts. "
            "Always check warning indicators first. If no indicators are active, review "
            "technique and ground conditions before involving maintenance."
        ),
    },
    {
        "id": "trouble_002",
        "title": "Troubleshooting — Abnormal Machine Behaviour",
        "section": "Troubleshooting",
        "tags": ["troubleshooting", "abnormal", "warning", "vibration", "noise", "fault"],
        "content": (
            "Warning signs that require immediate attention: "
            "1) Unusual banging, knocking, or squealing sounds from any component. "
            "2) Machine pulling to one side during travel (possible track or travel motor issue). "
            "3) Boom or arm drifting down without input (possible cylinder seal leak). "
            "4) Excessive black smoke from exhaust (engine issue — fuel, air, or injector). "
            "5) Steering or swing feeling sluggish or erratic. "
            "6) Any new or unexpected warning indicator. "
            "Response: stop work safely, lower the attachment to the ground, shut down if it is safe, "
            "and report to maintenance. Do not attempt to diagnose electrical or hydraulic faults yourself."
        ),
    },

    # ── MACHINE POSITIONING ───────────────────────────────────────────────────
    {
        "id": "positioning_001",
        "title": "Machine Positioning — Optimal Setup",
        "section": "Machine Positioning",
        "tags": ["positioning", "setup", "bench", "reach", "productivity"],
        "content": (
            "Correct machine positioning is fundamental to productive and safe operation: "
            "1) Position so the digging face is within the machine's optimal reach — typically "
            "70–80% of maximum reach. Operating at maximum extension reduces breakout force. "
            "2) The truck should be positioned so the operator can swing loaded with minimal angle. "
            "3) Keep the machine level — working on a lateral slope puts excessive load on "
            "one track and the swing ring. "
            "4) Maintain adequate distance from bench edges — a general guide is machine width "
            "plus 2 metres from the bench edge. "
            "5) Reposition frequently rather than stretching to reach — time spent repositioning "
            "is usually less than the productivity lost from poor reach angles."
        ),
    },

    # ── WORKING ON SLOPES ─────────────────────────────────────────────────────
    {
        "id": "slopes_001",
        "title": "Working on Slopes — Safe Operation",
        "section": "Slope Operation",
        "tags": ["slope", "stability", "safety", "terrain", "wet_ground"],
        "content": (
            "Slope operation increases tip-over risk significantly. Rules: "
            "1) Travel up and down slopes in a straight line — never turn on a slope. "
            "2) When going downhill, keep the attachment low (bucket close to ground) for stability. "
            "3) When going uphill, face uphill with the attachment trailing. "
            "4) Use slow, controlled travel speed on slopes — avoid sudden stops or starts. "
            "5) Know the machine's maximum gradeability — typically 35–40% for standard excavators, "
            "less in wet or muddy conditions. "
            "6) If the machine starts to slide, lower the attachment to the ground to act as a brake. "
            "7) Never park on a slope without chocking the tracks."
        ),
    },

    # ── MAINTENANCE AWARENESS ─────────────────────────────────────────────────
    {
        "id": "maintenance_001",
        "title": "Preventive Maintenance — Operator Role",
        "section": "Maintenance Awareness",
        "tags": ["maintenance", "inspection", "fluid", "lubrication", "filters"],
        "content": (
            "Operators play a key role in preventive maintenance: "
            "1) Report all faults, unusual sounds, and warning indicators on the machine logbook. "
            "2) Check engine oil, coolant, and hydraulic oil levels at the start of each shift. "
            "3) Grease all required lubrication points at the specified interval. "
            "4) Check air filter restriction indicator — a blocked air filter causes power loss and high fuel consumption. "
            "5) Inspect for any new fluid leaks at the start and end of each shift. "
            "6) Keep the cab clean — debris can block controls or interfere with foot pedals. "
            "Early fault reporting prevents minor issues from becoming major failures."
        ),
    },

    # ── TRAINING PLANS ────────────────────────────────────────────────────────
    {
        "id": "plan_beginner_001",
        "title": "Learning Path — New Operator",
        "section": "Training Plan",
        "tags": ["training_plan", "beginner", "new_operator", "learning_path"],
        "content": (
            "Suggested learning progression for a new excavator operator: "
            "Week 1: Machine familiarisation — components, cabin controls, safety systems, "
            "pre-operation inspection. "
            "Week 2: Basic operation — starting/stopping, travel, swing, basic digging in a safe area. "
            "Week 3: Excavation technique — bench work, truck loading, bucket filling. "
            "Week 4: Advanced operation — trenching, grading, slope work, wet conditions. "
            "Ongoing: Cycle time analysis, fuel efficiency, load management. "
            "Safety training must run in parallel throughout — not as a standalone module at the end."
        ),
    },
    {
        "id": "plan_productivity_001",
        "title": "Learning Path — Improving Productivity",
        "section": "Training Plan",
        "tags": ["training_plan", "productivity", "cycle_time", "fuel", "idle", "payload"],
        "content": (
            "7-day plan to improve excavation productivity: "
            "Day 1: Cycle time analysis — review current cycle times, identify swing angle and positioning issues. "
            "Day 2: Machine positioning — practice optimal setup for different bench configurations. "
            "Day 3: Swing technique — practice smooth loaded swing and early deceleration. "
            "Day 4: Bucket fill factor — practice filling the bucket efficiently in one or two passes. "
            "Day 5: Truck coordination — practice truck spotting signals and positioning for fast loading. "
            "Day 6: Idle time reduction — enable auto-idle, practice low-idle waiting habits. "
            "Day 7: Review — compare cycle times from day 1 to end of week. "
            "Target: 10–15% cycle time improvement through technique alone."
        ),
    },
    {
        "id": "plan_safety_001",
        "title": "Learning Path — Safety Focus",
        "section": "Training Plan",
        "tags": ["training_plan", "safety", "blind_zone", "exclusion_zone", "emergency"],
        "content": (
            "Safety-focused training plan: "
            "Day 1: Blind zone identification — walk around the machine and physically mark blind zones. "
            "Day 2: Exclusion zone setup — practice establishing and communicating exclusion zones. "
            "Day 3: Pre-operation inspection — practice thorough walk-around in under 10 minutes. "
            "Day 4: Wet ground and slope operation — theory and controlled practice. "
            "Day 5: Emergency procedures — practice machine shutdown and evacuation procedures. "
            "Day 6: Communication protocols — radio procedures with ground crew and truck drivers. "
            "Day 7: Review — identify any remaining gaps and plan follow-up training."
        ),
    },
]
