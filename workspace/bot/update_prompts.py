#!/usr/bin/env python3
"""Update all LoRA entries in lora_registry.json with 20-term prompts."""
import json, pathlib

REG_PATH = pathlib.Path(__file__).parent.parent / "lora_registry.json"
reg = json.loads(REG_PATH.read_text())
cats = reg["categories"]

# ── Negative prompt templates ────────────────────────────────────────────────
NEG_3D = ("blurry, low quality, bad anatomy, deformed limbs, extra fingers, "
          "missing limbs, watermark, text, logo, 2D flat, sketch, painting, "
          "overexposed, underexposed, noisy, pixelated, artifacts, grainy, "
          "out of focus, ugly, poorly drawn, bad proportions, clipping, "
          "seam visible, plastic glare, flat shading")

NEG_REAL = ("cartoon, anime, illustrated, blurry, low resolution, watermark, "
            "text, logo, bad anatomy, deformed, extra fingers, missing limbs, "
            "overexposed, underexposed, noise, grain, harsh shadows, "
            "unnatural skin, plastic skin, uncanny valley, bad proportions, "
            "poorly lit, flat lighting, ugly, mutilated, disfigured")

NEG_ANIME = ("realistic photo, blurry, bad anatomy, deformed, extra fingers, "
             "missing limbs, watermark, text, logo, low quality, artifacts, "
             "grainy, noisy, overexposed, underexposed, off-model, "
             "inconsistent style, poorly drawn, bad proportions, ugly, "
             "mutilated, disfigured, out of frame, cropped")

NEG_ART = ("photo realistic, blurry, low quality, watermark, text, logo, "
           "bad anatomy, deformed limbs, extra fingers, missing limbs, "
           "noisy, pixelated, overexposed, underexposed, messy strokes, "
           "unfinished, poorly composed, flat uninteresting, artifacts, "
           "inconsistent style, ugly, mutilated")

NEG_R18 = ("censored, mosaic, black bar, pixelated genitals, blurry, "
           "bad anatomy, deformed, extra limbs, missing limbs, watermark, "
           "text, logo, low quality, overexposed, flat lighting, ugly, "
           "poorly drawn, bad proportions, artifacts, grainy, out of frame")

# ─────────────────────────────────────────────────────────────────────────────
# 3D category
# ─────────────────────────────────────────────────────────────────────────────
cats["3d"]["loras"]["3D渲染风格"]["base_prompt"] = (
    "3D rendered character, smooth polished surface, studio white background, "
    "professional 3D figurine, PBR material shading, subsurface scattering skin, "
    "high-quality render, sharp details, ambient occlusion, dramatic studio light, "
    "collectible toy aesthetic, clean silhouette, plastic glossy finish, "
    "soft shadow, centered composition, turntable render angle, "
    "detailed facial features, vibrant saturated colors, depth of field bokeh, "
    "masterpiece render quality"
)
cats["3d"]["loras"]["3D渲染风格"]["negative_prompt"] = NEG_3D

cats["3d"]["loras"]["Q版娃娃"]["base_prompt"] = (
    "Q-version chibi doll, big round head, tiny cute body, oversized eyes, "
    "soft round proportions, pastel candy colors, glossy toy material, "
    "studio white background, 3D chibi render, adorable expression, "
    "chubby cheeks, miniature doll scale, smooth plastic texture, "
    "bright cheerful lighting, collectible blind box style, "
    "simplified cute hands, fluffy hair detail, clean crisp edges, "
    "charming tiny pose, high quality figurine render"
)
cats["3d"]["loras"]["Q版娃娃"]["negative_prompt"] = NEG_3D

cats["3d"]["loras"]["Q版角色"]["base_prompt"] = (
    "Q-version chibi character, large head to body ratio, adorable round face, "
    "expressive big eyes, simplified proportions, cute anime chibi style, "
    "3D render quality, clean smooth surfaces, pastel soft colors, "
    "studio white background, figurine scale, glossy material finish, "
    "charming tiny pose, chubby rounded limbs, cute accessories, "
    "bright cheerful lighting, sharp crisp render, collectible style, "
    "original character preserved, high quality chibi render"
)
cats["3d"]["loras"]["Q版角色"]["negative_prompt"] = NEG_3D

cats["3d"]["loras"]["芭比盲盒"]["base_prompt"] = (
    "Barbie-style fashion doll, slender elegant figure, trendy stylish outfit, "
    "blind box collectible toy, pastel pink and white palette, "
    "glossy plastic surface, studio white background, 3D render, "
    "chic fashionable clothing, high heels accessory, perfect makeup, "
    "long flowing hair, slim proportions, sparkle and shine detail, "
    "romantic soft lighting, collectible box aesthetic, "
    "detailed fabric texture on outfit, vibrant color pop, "
    "elegant standing pose, premium toy quality render"
)
cats["3d"]["loras"]["芭比盲盒"]["negative_prompt"] = NEG_3D

# ─────────────────────────────────────────────────────────────────────────────
# sanzhantu category
# ─────────────────────────────────────────────────────────────────────────────
NEG_SANV = ("single view only, blurry, bad anatomy, deformed, extra fingers, "
            "missing limbs, watermark, text overlapping design, messy lines, "
            "inconsistent scale between views, low quality, artifacts, "
            "background clutter, colored background, shadows, shading fills, "
            "incomplete third view, misaligned views, poorly drawn")

cats["sanzhantu"]["loras"]["三视图"]["base_prompt"] = (
    "character reference sheet turnaround, front view center, back view right, "
    "side profile left, clean precise linework, consistent character scale, "
    "white background, clear silhouette outline, detailed costume design, "
    "facial feature annotations, color palette swatches, height guide line, "
    "professional character design sheet, proportional accuracy, "
    "no shading flat color fill, hair detail from all angles, "
    "accessories shown from every view, shoes and feet detail, "
    "hand pose reference, uniform lighting, design reference quality"
)
cats["sanzhantu"]["loras"]["三视图"]["negative_prompt"] = NEG_SANV

cats["sanzhantu"]["loras"]["三视图Q版"]["base_prompt"] = (
    "chibi Q-version character reference sheet, three views front back side, "
    "cute big head small body proportion, round simplified features, "
    "white background, clean flat linework, consistent chibi scale, "
    "front view center, back view right, side view left, "
    "costume detail from all angles, hair from every direction, "
    "color palette flat fill, no shadow no shading, "
    "adorable expression reference, tiny cute hands and feet, "
    "accessories annotated, proportion guide, "
    "professional chibi design sheet, high quality illustration"
)
cats["sanzhantu"]["loras"]["三视图Q版"]["negative_prompt"] = NEG_SANV

cats["sanzhantu"]["loras"]["简单三视图"]["base_prompt"] = (
    "simple clean character reference turnaround, front back side views, "
    "minimal linework style, clear clean silhouette, white background, "
    "no unnecessary detail, essential shape language only, "
    "flat clean outline, consistent proportions across views, "
    "legible from small size, beginner-friendly design reference, "
    "clear facial feature placement, basic costume outline, "
    "three equidistant panels, same character scale, "
    "simple hair shape, no texture detail, clean professional lines, "
    "design communication priority, easy to read reference sheet"
)
cats["sanzhantu"]["loras"]["简单三视图"]["negative_prompt"] = NEG_SANV

# ─────────────────────────────────────────────────────────────────────────────
# xiesifengge category
# ─────────────────────────────────────────────────────────────────────────────
cats["xiesifengge"]["loras"]["Neobro颜"]["base_prompt"] = (
    "Neobro style cinematic portrait, dramatic chiaroscuro lighting, "
    "deep shadow contrast, hyperrealistic skin pore detail, "
    "intense brooding gaze, editorial fashion photography, "
    "moody atmospheric dark background, sharp crisp focus, "
    "high fashion editorial mood, film noir aesthetic, "
    "deep blacks rich shadows, specular skin highlight, "
    "strong jaw dramatic face, commercial photography quality, "
    "85mm lens portrait compression, bokeh background blur, "
    "raw masculine power aesthetic, studio strobe lighting, "
    "color graded cinematic tones, professional retouching, "
    "award-winning portrait photography"
)
cats["xiesifengge"]["loras"]["Neobro颜"]["negative_prompt"] = NEG_REAL

cats["xiesifengge"]["loras"]["亚洲美女"]["base_prompt"] = (
    "beautiful Asian woman portrait, natural elegant features, "
    "smooth radiant skin texture, bright almond-shaped eyes, "
    "soft natural makeup, professional portrait photography, "
    "warm flattering studio light, natural hair flowing, "
    "refined delicate facial features, clear clean complexion, "
    "fashionable modern styling, natural background blur bokeh, "
    "authentic Asian beauty aesthetic, high resolution detail, "
    "professional color grading, sharp in-focus eyes, "
    "subtle smile expression, confident posture, "
    "clean simple background, magazine-quality portrait, "
    "natural beauty photographic realism"
)
cats["xiesifengge"]["loras"]["亚洲美女"]["negative_prompt"] = NEG_REAL

cats["xiesifengge"]["loras"]["少女白灵"]["base_prompt"] = (
    "delicate young girl portrait, ethereal porcelain fair skin, "
    "dreamlike soft-focus glow, gentle innocent expression, "
    "Chinese beauty aesthetic, dewy luminous complexion, "
    "soft diffused natural light, wispy flowing hair, "
    "translucent skin quality, large clear bright eyes, "
    "subtle pink lips, pure clean background, "
    "romantic dreamy atmosphere, soft pastel color tones, "
    "youthful grace and elegance, gossamer fabric detail, "
    "high key soft lighting, fine hair strand detail, "
    "celestial fairy-like quality, high resolution portrait"
)
cats["xiesifengge"]["loras"]["少女白灵"]["negative_prompt"] = NEG_REAL

cats["xiesifengge"]["loras"]["索尼色彩"]["base_prompt"] = (
    "Sony camera color profile portrait, natural accurate skin tones, "
    "clean highlight roll-off, vivid yet realistic color science, "
    "professional photography color accuracy, shadow detail retention, "
    "Sony Alpha color rendering, crisp sharp resolution, "
    "natural daylight white balance, accurate color reproduction, "
    "clean noise-free image, professional lens sharpness, "
    "natural saturation without oversaturation, true-to-life colors, "
    "fine micro-contrast detail, Sony sensor dynamic range, "
    "realistic color temperature, professional color calibration, "
    "clean skin tone gradation, faithful color capture, "
    "documentary photography quality"
)
cats["xiesifengge"]["loras"]["索尼色彩"]["negative_prompt"] = NEG_REAL

cats["xiesifengge"]["loras"]["网红脸"]["base_prompt"] = (
    "internet celebrity makeup look, smooth flawless porcelain skin, "
    "enlarged bright double eyelids, perfect symmetrical face, "
    "K-beauty gradient lip, contoured cheekbones, "
    "influencer social media aesthetic, trendy eye makeup, "
    "V-shaped jaw line, small delicate nose, "
    "dewy glow highlighter, fake lashes volume, "
    "neutral warm filter tone, beauty blogger style, "
    "perfect brow shape, glossy lip finish, "
    "pore-free retouched skin, modern trendy style, "
    "Chinese social media beauty standard, "
    "professional studio portrait quality"
)
cats["xiesifengge"]["loras"]["网红脸"]["negative_prompt"] = NEG_REAL

cats["xiesifengge"]["loras"]["超级写实系"]["base_prompt"] = (
    "ultra hyperrealistic portrait, extreme 8K detail, "
    "microscopic skin pore texture, subsurface scattering realism, "
    "physically accurate light simulation, photographic realism, "
    "individual hair strand detail, iris and cornea detail, "
    "capillary blood vessel visible skin, micro skin texture, "
    "specular highlight accuracy, depth accurate shadow casting, "
    "photographic grain and film latitude, physically-based rendering, "
    "real-world lens characteristics, camera sensor realism, "
    "unretouched raw natural look, facial muscle detail, "
    "accurate environmental reflection, documentary photography truth, "
    "indistinguishable from real photograph"
)
cats["xiesifengge"]["loras"]["超级写实系"]["negative_prompt"] = NEG_REAL

cats["xiesifengge"]["loras"]["韩国风格"]["base_prompt"] = (
    "Korean beauty aesthetic portrait, glass skin luminous glow, "
    "gradient soft lips, cloud-like fluffy hair, "
    "dewy healthy skin sheen, K-beauty natural makeup, "
    "soft peach skin tone, effortless chic styling, "
    "Korean fashion magazine quality, clean minimal aesthetic, "
    "double eyelid natural look, cute innocent expression, "
    "soft diffused studio light, milky smooth complexion, "
    "Korean idol beauty standard, warm beige color tone, "
    "natural brow styling, subtle blush pink cheeks, "
    "effortless hair flow, professional Korean portrait photography"
)
cats["xiesifengge"]["loras"]["韩国风格"]["negative_prompt"] = NEG_REAL

# ─────────────────────────────────────────────────────────────────────────────
# dongman category
# ─────────────────────────────────────────────────────────────────────────────
cats["dongman"]["loras"]["Dreamwave"]["base_prompt"] = (
    "dreamwave synthwave aesthetic, neon purple and pink glow, "
    "retro-futuristic vaporwave atmosphere, glowing neon grid, "
    "sunset retrowave color palette, ethereal dream-like haze, "
    "glowing eyes laser beams, cyberpunk neon city background, "
    "holographic iridescent sheen, electric blue accent light, "
    "80s aesthetic nostalgia, synthwave music visual art, "
    "anime illustration style, luminous bloom effect, "
    "chrome metallic reflections, starfield night sky, "
    "outrun aesthetic color grade, dramatic backlit silhouette, "
    "detailed anime character, high quality digital art"
)
cats["dongman"]["loras"]["Dreamwave"]["negative_prompt"] = NEG_ANIME

cats["dongman"]["loras"]["Q版"]["base_prompt"] = (
    "chibi Q-version anime style, 1:2 head-to-body ratio, "
    "enormous round expressive eyes, chubby rosy cheeks, "
    "tiny cute hands and feet, simplified round silhouette, "
    "bright cheerful pastel colors, adorable chibi expression, "
    "clean cel-shaded coloring, simple costume design, "
    "bouncy fluffy hair, round button nose, "
    "exaggerated cute emotion, clean ink outline, "
    "flat color manga style, star-shaped sparkle eyes, "
    "miniature cute proportions, joyful playful mood, "
    "classic Japanese chibi anime, high quality illustration"
)
cats["dongman"]["loras"]["Q版"]["negative_prompt"] = NEG_ANIME

cats["dongman"]["loras"]["仙侠修仙"]["base_prompt"] = (
    "xianxia cultivation fantasy art, celestial flowing silk robes, "
    "mystical qi energy aura glowing, ancient Chinese immortal, "
    "mountain peaks and clouds background, ethereal sword flying, "
    "divine cultivation realm aesthetic, lotus blossom scatter, "
    "golden dao energy visual, moonlit night cultivation scene, "
    "intricate traditional Chinese embroidery, immortal elder beauty, "
    "heavenly realm composition, spiritual power eruption, "
    "jade ornament accessories, flowing long hair in wind, "
    "ancient seal script rune effects, immortal transcendence pose, "
    "detailed anime illustration, high quality xianxia art"
)
cats["dongman"]["loras"]["仙侠修仙"]["negative_prompt"] = NEG_ANIME

cats["dongman"]["loras"]["古典美女"]["base_prompt"] = (
    "classical Chinese beauty, elegant traditional hanfu dress, "
    "refined ancient Chinese hairstyle with jade ornaments, "
    "palace courtyard background, ink painting brush influence, "
    "delicate embroidered fabric detail, serene dignified expression, "
    "classical beauty canon features, fan or qin instrument prop, "
    "flowing layered silk garment, ornate hairpin accessory, "
    "gentle morning mist atmosphere, plum blossom or lotus motif, "
    "ancient Chinese painting composition, warm golden candlelight, "
    "graceful elegant pose, refined aristocratic lady, "
    "traditional Chinese color palette, literary artistic atmosphere, "
    "high quality classical Chinese illustration"
)
cats["dongman"]["loras"]["古典美女"]["negative_prompt"] = NEG_ANIME

cats["dongman"]["loras"]["江南美女"]["base_prompt"] = (
    "Jiangnan water town beauty, misty rain river scene, "
    "elegant woman in traditional Chinese dress, "
    "ancient stone bridge and canal background, ink wash painting influence, "
    "delicate southern China features, gentle soft expression, "
    "white-washed architecture background, willow tree reflection, "
    "light fabric flowing in breeze, quiet scholarly atmosphere, "
    "poetry and painting aesthetic, lotus pond scenery, "
    "classical Chinese garden setting, soft drizzle rain mood, "
    "refined feminine grace, green bamboo accent, "
    "traditional ink painting color palette, watercolor wash effect, "
    "peaceful Suzhou garden scene, high quality Chinese art"
)
cats["dongman"]["loras"]["江南美女"]["negative_prompt"] = NEG_ANIME

cats["dongman"]["loras"]["浮光跃金_v1.0"]["base_prompt"] = (
    "golden floating light effect, shimmering liquid gold highlights, "
    "luxury gold foil texture overlay, scattered golden particle rain, "
    "rich metallic gold sheen, glittering gold dust atmosphere, "
    "golden light streak bokeh, warm amber and gold color palette, "
    "iridescent gold surface reflections, sunlit gold sparkle, "
    "premium luxury visual aesthetic, gilded golden frame glow, "
    "glowing golden energy aura, gold leaf flake detail, "
    "radiant warm golden backlight, opulent golden atmosphere, "
    "metallic gold costume embellishment, golden crown accessory, "
    "high quality luxury anime illustration, detailed artwork"
)
cats["dongman"]["loras"]["浮光跃金_v1.0"]["negative_prompt"] = NEG_ANIME

cats["dongman"]["loras"]["璀璨流光"]["base_prompt"] = (
    "brilliant flowing light streaks, luminous colorful light trails, "
    "dazzling sparkle particle effect, iridescent rainbow light arc, "
    "glowing neon light ribbon, speed motion light blur, "
    "prismatic color spectrum glow, magical light emission, "
    "radiant energy beam effect, crystal prism refraction, "
    "starlight scatter background, glowing emission shader, "
    "dynamic light motion blur, colorful aurora effect, "
    "shining light trail path, luminous bloom overdrive, "
    "electric plasma discharge art, kaleidoscope light effect, "
    "stunning visual spectacle, high quality digital illustration"
)
cats["dongman"]["loras"]["璀璨流光"]["negative_prompt"] = NEG_ANIME

cats["dongman"]["loras"]["艺术涂鸦"]["base_prompt"] = (
    "urban graffiti street art style, spray paint layered texture, "
    "expressive brushstroke doodle, colorful tagging mural, "
    "street artist aesthetic, bold thick outline, "
    "vibrant saturated graffiti colors, concrete wall background, "
    "wildstyle lettering influence, character tag artwork, "
    "drip paint effect, sticker bomb aesthetic, "
    "raw expressive line quality, mixed media art style, "
    "culture street art scene, hip-hop visual art influence, "
    "throwback graffiti culture, artist hand-crafted feel, "
    "urban contemporary art, high quality street art illustration"
)
cats["dongman"]["loras"]["艺术涂鸦"]["negative_prompt"] = NEG_ANIME

# ─────────────────────────────────────────────────────────────────────────────
# huazuo category
# ─────────────────────────────────────────────────────────────────────────────
cats["huazuo"]["loras"]["中国水墨"]["base_prompt"] = (
    "Chinese ink wash painting, spontaneous brushstroke technique, "
    "sumi-e black ink gradients on xuan paper, calligraphy brush quality, "
    "wet-on-wet ink diffusion, traditional Chinese painting aesthetic, "
    "negative space composition, ink concentration variation, "
    "monochrome ink tones, brush loading and dry stroke contrast, "
    "silk mounting presentation, seal stamp red chop, "
    "literati painting atmosphere, mountain mist landscape elements, "
    "bamboo or plum motif accent, scholar's painting aesthetic, "
    "spontaneous gestural quality, Chinese art museum quality, "
    "authentic ink on rice paper texture, masterpiece ink painting"
)
cats["huazuo"]["loras"]["中国水墨"]["negative_prompt"] = ("colorful, oil paint, digital neon, blurry, watermark, text, logo, "
    "bad anatomy, deformed, extra fingers, missing limbs, overexposed, "
    "underexposed, noisy, pixelated, artifacts, grainy, harsh light, "
    "photo realistic, bright saturated colors, western art style, "
    "poorly composed, flat uninteresting, ugly, mutilated")

cats["huazuo"]["loras"]["水墨人物"]["base_prompt"] = (
    "Chinese ink figure painting, expressive brushwork portrait, "
    "ink wash technique on xuan paper, calligraphic line quality, "
    "monochrome ink tones from pale gray to deep black, "
    "traditional Chinese figure art, scholar or lady subject, "
    "flowing ink robe rendering, gestural face outline, "
    "loose expressive brushstroke body, ink pooling and spreading, "
    "negative white space utilization, classical Chinese figure canon, "
    "seal script chop stamp, hanging scroll composition, "
    "literati aesthetic, subtle ink shading, "
    "museum quality Chinese figure painting, authentic ink medium, "
    "high level brushwork mastery, classical masterpiece"
)
cats["huazuo"]["loras"]["水墨人物"]["negative_prompt"] = ("colorful fills, oil paint, digital art, blurry, watermark, text, "
    "bad anatomy, deformed limbs, extra fingers, missing limbs, "
    "overexposed, underexposed, noisy, artifacts, harsh light, "
    "western portrait style, photo realistic, bright colors, "
    "poorly drawn, bad proportions, ugly, disfigured, mutilated")

cats["huazuo"]["loras"]["油画1"]["base_prompt"] = (
    "classical oil painting on canvas, thick impasto brushstroke texture, "
    "linen canvas weave visible, rich saturated oil pigment, "
    "old master glazing technique, warm Rembrandt lighting, "
    "deep chiaroscuro shadow to light, accurate color mixing, "
    "fine detail in highlights, loose gestural background, "
    "museum-quality oil portrait, varnished surface sheen, "
    "traditional oil medium layering, painterly aesthetic, "
    "classical European portrait composition, masterful brushwork, "
    "Renaissance or Baroque influence, earthy color palette, "
    "dimensional paint surface, authentic oil painting quality"
)
cats["huazuo"]["loras"]["油画1"]["negative_prompt"] = NEG_ART

cats["huazuo"]["loras"]["石像"]["base_prompt"] = (
    "stone sculpture, carved granite or marble figure, "
    "weathered ancient stone texture, chisel mark detail, "
    "museum ancient sculpture quality, monochrome stone tones, "
    "heavy solid mass aesthetic, archaic stylized features, "
    "stone surface patina and aging, classical sculpture composition, "
    "pedestal display presentation, museum gallery lighting, "
    "ancient Greek or Chinese stone tradition, durable permanence aesthetic, "
    "rock crystal and mineral inclusions, carved relief detail, "
    "archaeological artifact quality, stone weight and gravity, "
    "monolithic powerful presence, museum conservation quality, "
    "high resolution stone material render"
)
cats["huazuo"]["loras"]["石像"]["negative_prompt"] = ("painting, colorful, blurry, bad anatomy, watermark, text, logo, "
    "deformed, extra fingers, missing limbs, overexposed, underexposed, "
    "noisy, pixelated, artifacts, grainy, flesh skin color, "
    "soft material, fabric, photo of person, poorly sculpted, "
    "bad proportions, ugly, mutilated, disfigured")

cats["huazuo"]["loras"]["线稿"]["base_prompt"] = (
    "clean line art drawing, precise technical linework, "
    "no color fill pure outline, black ink on white paper, "
    "detailed pencil or pen illustration, crisp sharp line quality, "
    "consistent line weight variation, technical illustration standard, "
    "no shading no gray fill, architectural drawing precision, "
    "character outline blueprint style, accurate anatomy line guide, "
    "professional inking technique, cross-hatching detail optional, "
    "clean white negative space, draft illustration quality, "
    "anime-style clean inking, fashion illustration linework, "
    "precise and deliberate strokes, professional line art quality"
)
cats["huazuo"]["loras"]["线稿"]["negative_prompt"] = ("color fill, blurry, messy lines, watermark, text, logo, "
    "bad anatomy, deformed, extra fingers, missing limbs, shading, "
    "gradient fill, colored background, overexposed, pixelated, "
    "noisy, low quality, artifacts, sketchy loose lines, "
    "incomplete outlines, crossing messy strokes, poorly drawn")

# ─────────────────────────────────────────────────────────────────────────────
# fenggehua category
# ─────────────────────────────────────────────────────────────────────────────
cats["fenggehua"]["loras"]["RX78"]["base_prompt"] = (
    "Gundam RX-78-2 mecha transformation, giant mechanical robot armor, "
    "steel panel segment joints, cockpit visor detail, "
    "beam rifle and shield weapon, yellow V-fin head crest, "
    "white red blue Gundam color scheme, mechanical joint articulation, "
    "sci-fi mecha design quality, metallic surface reflections, "
    "mobile suit scale in space or battlefield, "
    "thruster exhaust heat glow, antenna sensor array, "
    "battle damage weathering optional, mechanical chest reactor, "
    "Universal Century Gundam aesthetic, action dynamic pose, "
    "mecha anime illustration quality, detailed panel line art, "
    "epic scale dramatic lighting, high quality mecha render"
)
cats["fenggehua"]["loras"]["RX78"]["negative_prompt"] = NEG_3D

cats["fenggehua"]["loras"]["冻结"]["base_prompt"] = (
    "frozen suspended in crystal clear ice, ice encasing figure completely, "
    "cold blue and white ice tones, frost crystal formation detail, "
    "air bubble trapped in ice, suspended in frozen time, "
    "ice refraction and caustic light, cracked ice surface texture, "
    "preservation in glacier ice, frozen expression moment, "
    "snow flake and ice shard scatter, sub-zero temperature aesthetic, "
    "deep blue cold color palette, frozen solid ice block sculpture, "
    "ice clarity transparency effect, crisp sharp ice edge, "
    "arctic freeze visual metaphor, cold winter elemental power, "
    "dramatic ice entombment composition, high quality frozen art"
)
cats["fenggehua"]["loras"]["冻结"]["negative_prompt"] = NEG_3D

cats["fenggehua"]["loras"]["婚纱1"]["base_prompt"] = (
    "elegant traditional bridal gown, floor-length white wedding dress, "
    "delicate lace and embroidery detail, cathedral veil flowing, "
    "romantic floral bouquet accessory, pearl and crystal embellishment, "
    "soft romantic studio lighting, ivory white fabric drape, "
    "corseted fitted bodice, full ballgown skirt silhouette, "
    "classic bridal portrait composition, elegant updo hairstyle, "
    "chapel or garden background, soft rose petal scatter, "
    "timeless bridal elegance, diamond jewelry detail, "
    "pure white bridal palette, romantic dreamy atmosphere, "
    "wedding photography quality, high quality bridal portrait"
)
cats["fenggehua"]["loras"]["婚纱1"]["negative_prompt"] = NEG_REAL

cats["fenggehua"]["loras"]["婚纱2"]["base_prompt"] = (
    "modern contemporary wedding dress, sleek minimalist bridal style, "
    "clean tailored silhouette, architectural fashion-forward gown, "
    "modern bridal editorial photography, fashionable designer dress, "
    "structured bodice with minimal lace, chic simple elegance, "
    "soft neutral backdrop, fashion magazine bridal shoot, "
    "modern couture aesthetic, statement earrings accessory, "
    "sculptural fabric drape, asymmetric contemporary design, "
    "clean crisp white fabric, modern minimalist bridal aesthetic, "
    "high fashion bridal portrait, editorial lighting setup, "
    "confident modern bride pose, professional fashion photography"
)
cats["fenggehua"]["loras"]["婚纱2"]["negative_prompt"] = NEG_REAL

cats["fenggehua"]["loras"]["宠物之家"]["base_prompt"] = (
    "cute cozy pet house diorama, tiny adorable animal characters, "
    "miniature cozy interior design, warm soft home lighting, "
    "fluffy pet bed and toys, pastel home decor palette, "
    "small window with sunshine streaming, miniature furniture detail, "
    "warm fireplace glow, pet portraits on tiny walls, "
    "cozy wooden floor texture, soft textile cushions, "
    "adorable pet lifestyle illustration, charming animal character design, "
    "storybook home aesthetic, warm family atmosphere, "
    "detailed miniature scale, kawaii pet art style, "
    "heartwarming illustration quality, high quality diorama render"
)
cats["fenggehua"]["loras"]["宠物之家"]["negative_prompt"] = NEG_3D

cats["fenggehua"]["loras"]["微缩世界"]["base_prompt"] = (
    "tilt-shift miniature world photography effect, "
    "dollhouse scale tiny people and vehicles, macro lens aesthetic, "
    "selective focus blur top and bottom, miniature diorama landscape, "
    "toy-like city from above aerial view, "
    "hyperreal miniature model quality, tiny scale buildings, "
    "vivid saturated toy colors, shallow depth of field, "
    "miniature model railroad aesthetic, small world charm, "
    "perfectly crafted scale scene, detailed miniature figures, "
    "warm sunlight on tiny world, artisan model making quality, "
    "architecture miniature display, Gulliver perspective scale, "
    "creative photography concept, high quality miniature art"
)
cats["fenggehua"]["loras"]["微缩世界"]["negative_prompt"] = NEG_3D

cats["fenggehua"]["loras"]["扁平风格插画"]["base_prompt"] = (
    "flat design vector illustration, solid color geometric shapes, "
    "clean minimal graphic design, no shadow no gradient, "
    "bold simple silhouette, flat 2D character design, "
    "Scandinavian minimalist aesthetic, geometric pattern background, "
    "primary bold color palette, clean line boundary, "
    "icon and infographic style, UI illustration aesthetic, "
    "simple readable composition, app icon design quality, "
    "flat color fill no texture, modern design trend, "
    "simple elegant visual communication, creative vector art, "
    "professional graphic design quality, high quality flat illustration"
)
cats["fenggehua"]["loras"]["扁平风格插画"]["negative_prompt"] = ("realistic photo, 3D render, shadow, gradient, blurry, watermark, "
    "bad anatomy, deformed, extra fingers, missing limbs, noisy, "
    "pixelated, overexposed, underexposed, texture detail, "
    "complex background, cluttered composition, ugly, mutilated")

cats["fenggehua"]["loras"]["描金画玉"]["base_prompt"] = (
    "Chinese gold painting on dark lacquer, intricate gold foil pattern, "
    "traditional Chinese decorative art, gold-on-black lacquer ware, "
    "ornate golden floral motif, ancestral jade and gold craft, "
    "rich luxury decorative texture, gold leaf application detail, "
    "imperial palace art aesthetic, phoenix and dragon gold motif, "
    "Ming or Qing dynasty decorative art, meticulous gold brushwork, "
    "dark vermilion or black base color, opulent luxurious quality, "
    "museum-quality Chinese art object, detailed gold inlay work, "
    "cultural heritage craft excellence, radiant gold against dark ground, "
    "masterpiece Chinese traditional art"
)
cats["fenggehua"]["loras"]["描金画玉"]["negative_prompt"] = NEG_ART

cats["fenggehua"]["loras"]["毛茸茸3D"]["base_prompt"] = (
    "fluffy plush stuffed animal 3D render, soft dense fur texture, "
    "plushie toy material quality, cuddly stuffed toy aesthetic, "
    "soft toy craftsmanship, cotton-filled round body shape, "
    "embroidered button eyes, sewn seam detail, "
    "pastel soft color palette, cozy warm lighting, "
    "photorealistic fur strand simulation, toy store display quality, "
    "giant fluffy teddy bear scale, collectible plush toy, "
    "handcrafted artisan stuffed animal, soft velvet or fleece material, "
    "studio white background, adorable stuffed character, "
    "premium toy manufacturing quality, high quality plush render"
)
cats["fenggehua"]["loras"]["毛茸茸3D"]["negative_prompt"] = NEG_3D

cats["fenggehua"]["loras"]["百花酿"]["base_prompt"] = (
    "blooming flower garden aesthetic, floral petal cascade, "
    "spring blossom shower atmosphere, flower-adorned clothing, "
    "floral crown and hair decoration, romantic garden setting, "
    "peony rose cherry blossom arrangement, pastel floral color palette, "
    "petal rain falling effect, lush botanical background, "
    "delicate flower texture on fabric, floral pattern overlay, "
    "fragrant garden atmosphere, soft spring light, "
    "flower wreath accessory, botanical illustration influence, "
    "abundance of blossoms composition, fairy-tale garden, "
    "romantic floral fantasy, high quality floral art"
)
cats["fenggehua"]["loras"]["百花酿"]["negative_prompt"] = NEG_ANIME

cats["fenggehua"]["loras"]["神相法身"]["base_prompt"] = (
    "divine deity celestial manifestation, golden halo aureole, "
    "multiple sacred arms holding artifacts, Buddhist or Daoist iconography, "
    "heavenly realm cloud background, sacred light emanation, "
    "deity transformation ritual pose, lotus throne seat, "
    "sacred geometric mandala pattern, divine armor and crown, "
    "spiritual energy aura glow, ancient temple wall painting style, "
    "Chinese deity canon aesthetic, vermilion and gold color scheme, "
    "religious iconographic composition, divine face serene expression, "
    "supernatural scale and power, sacred artifact weapons, "
    "celestial being transcendence, high quality deity illustration"
)
cats["fenggehua"]["loras"]["神相法身"]["negative_prompt"] = NEG_ANIME

cats["fenggehua"]["loras"]["粘土世界"]["base_prompt"] = (
    "polymer clay sculpture art, handmade clay texture detail, "
    "stop-motion animation aesthetic, clay figure artisan craft, "
    "smooth and fingerprint clay surface, vivid saturated clay colors, "
    "Wallace and Gromit claymation influence, clay world diorama, "
    "pinch and roll clay technique visible, clay eye detail, "
    "thick clay body proportions, cozy warm lighting on clay, "
    "artisan handcrafted quality, naive charm aesthetic, "
    "clay baked oven texture, rounded soft forms, "
    "creative clay character design, playful clay world, "
    "professional clay sculpture photography, high quality clay art"
)
cats["fenggehua"]["loras"]["粘土世界"]["negative_prompt"] = NEG_3D

cats["fenggehua"]["loras"]["透明火焰泛光裙子"]["base_prompt"] = (
    "transparent flame-effect dress, fire burning through sheer fabric, "
    "iridescent heat glow refraction, flame color gradient on cloth, "
    "ember sparks flying from dress, translucent fire material skirt, "
    "red orange yellow flame palette, supernatural fire magic aesthetic, "
    "glowing fire aura surrounding figure, heat distortion shimmer, "
    "fire elemental power visual, burning luminous fabric, "
    "fantasy flame costume design, dramatic fire lighting, "
    "phoenix fire element theme, intense heat energy glow, "
    "magical incandescent dress effect, high contrast fire and dark, "
    "spectacular visual effect quality, high quality fantasy art"
)
cats["fenggehua"]["loras"]["透明火焰泛光裙子"]["negative_prompt"] = NEG_ANIME

cats["fenggehua"]["loras"]["露营与海滩"]["base_prompt"] = (
    "summer outdoor camping beach lifestyle, ocean wave and seaside setting, "
    "beach tent camping setup, golden hour sunset glow, "
    "casual summer outfit, sandy beach bare feet, "
    "hammock or campfire scene, tropical paradise atmosphere, "
    "turquoise ocean water backdrop, sunshine and warm breeze, "
    "outdoor adventure spirit, beach bonfire evening, "
    "summer vacation carefree mood, coastal natural environment, "
    "bikini or casual beach wear, surfboard or beach umbrella prop, "
    "lifestyle photography quality, authentic outdoor setting, "
    "relaxed summer portrait, high quality outdoor photography"
)
cats["fenggehua"]["loras"]["露营与海滩"]["negative_prompt"] = NEG_REAL

# ─────────────────────────────────────────────────────────────────────────────
# zaxiang_sfw category
# ─────────────────────────────────────────────────────────────────────────────
NEG_SFW = ("blurry, bad anatomy, deformed, extra fingers, missing limbs, "
           "watermark, text, logo, low quality, artifacts, grainy, noisy, "
           "overexposed, underexposed, poorly drawn, bad proportions, "
           "ugly, mutilated, disfigured, out of frame, cropped, "
           "inconsistent style")

cats["zaxiang_sfw"]["loras"]["手办制造_comfyui"]["base_prompt"] = (
    "handcrafted collectible figurine, smooth PVC plastic surface, "
    "studio white background, premium figurine quality, "
    "same character identity preserved, anime figure scale, "
    "detailed face sculpt, accurate costume reproduction, "
    "high gloss finish on figurine, professional photography lighting, "
    "collector-grade figure detail, turntable render composition, "
    "figurine base pedestal, accurate color paintwork, "
    "fine hair sculpt detail, miniature scale props, "
    "Japanese PVC figure aesthetic, limited edition collectible quality, "
    "sharp detail render, masterpiece figurine production"
)
cats["zaxiang_sfw"]["loras"]["手办制造_comfyui"]["negative_prompt"] = NEG_SFW

cats["zaxiang_sfw"]["loras"]["XL手办风"]["base_prompt"] = (
    "XL scale premium collectible figurine, oversized display figure, "
    "detailed large-scale sculpt, studio photography setup, "
    "same character preserved in figurine, high-resolution surface detail, "
    "premium resin or PVC material, dramatic studio light on figure, "
    "accurate character faithful recreation, dynamic display pose, "
    "collector-grade paint application, sharp crisp figurine edges, "
    "professional figure photography, detailed accessories sculpt, "
    "XL size impressive scale presence, white or neutral background, "
    "luxury collector edition quality, fine craftsmanship detail, "
    "museum-quality figure display, masterpiece figurine"
)
cats["zaxiang_sfw"]["loras"]["XL手办风"]["negative_prompt"] = NEG_SFW

cats["zaxiang_sfw"]["loras"]["90年代动漫"]["base_prompt"] = (
    "1990s anime aesthetic, retro vintage cel-shaded animation, "
    "VHS film grain texture, old-school anime art style, "
    "classic 90s character design, hand-drawn cel animation quality, "
    "muted nostalgic color palette, 4:3 aspect ratio feel, "
    "classic anime big eyes style, vintage shojo or shonen aesthetic, "
    "retro anime hair design, nostalgic childhood cartoon feel, "
    "rough hand-drawn line quality, classic anime facial structure, "
    "old Gainax or Toei animation influence, analog video look, "
    "classic anime battle or romance, 90s fashion in anime, "
    "genuine retro animation nostalgia, high quality retro anime art"
)
cats["zaxiang_sfw"]["loras"]["90年代动漫"]["negative_prompt"] = NEG_ANIME

cats["zaxiang_sfw"]["loras"]["TS手工模型"]["base_prompt"] = (
    "handmade artisan model figure, workshop craft texture, "
    "handbuilt model kit assembly, visible craft material texture, "
    "detailed handcrafted sculpt work, artisan craftsperson quality, "
    "scratch-built model making, workshop photography setting, "
    "authentic hand-tool marks, natural material texture, "
    "detailed model builder precision, craft fair display quality, "
    "same character rendered as model, artist's craft process visible, "
    "natural studio lighting on model, textured material surface, "
    "bespoke handcrafted uniqueness, artisan figure quality, "
    "authentic model building craft, high quality craft photography"
)
cats["zaxiang_sfw"]["loras"]["TS手工模型"]["negative_prompt"] = NEG_SFW

cats["zaxiang_sfw"]["loras"]["BD2千夜"]["base_prompt"] = (
    "千夜 Chiyoru character from Brown Dust 2, dark mysterious outfit, "
    "long dark hair, gothic or dark fantasy costume design, "
    "game character official art quality, detailed armor or dress, "
    "BD2 game style illustration, expressive character portrait, "
    "accurate character design faithful recreation, "
    "anime game art quality, detailed accessory and weapon, "
    "character idle or battle pose, rich detailed background optional, "
    "vibrant game-quality color, sharp clean linework, "
    "official character art level quality, dynamic lighting, "
    "authentic BD2 aesthetic, high quality game illustration"
)
cats["zaxiang_sfw"]["loras"]["BD2千夜"]["negative_prompt"] = NEG_ANIME

cats["zaxiang_sfw"]["loras"]["BD2天顶"]["base_prompt"] = (
    "天顶 Zenith character from Brown Dust 2, mechanical or holy design, "
    "detailed armor or costume, BD2 game art style, "
    "expressive anime character portrait, accurate game character design, "
    "official game illustration quality, dynamic character pose, "
    "detailed weapon or accessory, vibrant game color palette, "
    "clean sharp anime linework, character card art quality, "
    "faithful BD2 character recreation, dramatic lighting effect, "
    "high resolution game illustration, professional anime art, "
    "character lore-accurate costume detail, game art masterpiece quality"
)
cats["zaxiang_sfw"]["loras"]["BD2天顶"]["negative_prompt"] = NEG_ANIME

cats["zaxiang_sfw"]["loras"]["BD2威廉娜"]["base_prompt"] = (
    "威廉娜 Wilhelmina character from Brown Dust 2, elegant noble costume, "
    "BD2 game art illustration style, detailed dress and accessory, "
    "expressive anime character portrait, accurate character design, "
    "official game art quality, noble aristocratic aesthetic, "
    "detailed fabric and lace ornament, character battle or idle pose, "
    "vibrant game illustration color, sharp clean line quality, "
    "faithful BD2 character recreation, dramatic studio lighting, "
    "high resolution anime game art, professional illustration, "
    "character lore-accurate costume, game card art quality"
)
cats["zaxiang_sfw"]["loras"]["BD2威廉娜"]["negative_prompt"] = NEG_ANIME

cats["zaxiang_sfw"]["loras"]["BD2日蚀"]["base_prompt"] = (
    "日蚀 Eclipse character from Brown Dust 2, solar eclipse theme design, "
    "dramatic dark and light contrast costume, BD2 game art style, "
    "expressive anime character portrait, accurate game character design, "
    "official illustration quality, detailed outfit and accessory, "
    "eclipse solar motif element, vibrant game color, "
    "sharp clean anime linework, dramatic lighting effect, "
    "faithful BD2 character recreation, high resolution game art, "
    "professional anime illustration, character lore-accurate, "
    "game card illustration quality, masterpiece game art"
)
cats["zaxiang_sfw"]["loras"]["BD2日蚀"]["negative_prompt"] = NEG_ANIME

cats["zaxiang_sfw"]["loras"]["体操短裤"]["base_prompt"] = (
    "gymnastics athletic bloomers outfit, tight-fitting sports uniform, "
    "gymnastics competition leotard with shorts, athletic dynamic pose, "
    "sports photography quality, gym floor or mat background, "
    "flexible athletic body, sports performance expression, "
    "cheerful athletic confidence, competition uniform design, "
    "clean sports illustration, bright gym or arena lighting, "
    "gymnastics routine pose, detailed sports uniform texture, "
    "athletic figure proportion, competitive sport spirit, "
    "professional sports photography, authentic gymnastics outfit, "
    "energy and dynamism, high quality sports illustration"
)
cats["zaxiang_sfw"]["loras"]["体操短裤"]["negative_prompt"] = NEG_SFW

cats["zaxiang_sfw"]["loras"]["佩可莉姆"]["base_prompt"] = (
    "Pecorine character from Princess Connect Re:Dive, "
    "golden blonde twin drill pigtails, white and gold armor knight outfit, "
    "cheerful bright smile expression, red eye color, "
    "signature sword and shield, anime game official art quality, "
    "accurate character design recreation, vibrant game color palette, "
    "clean sharp anime illustration, character card art quality, "
    "princess knight fantasy setting, accurate accessory detail, "
    "warm friendly character expression, dynamic hero pose, "
    "professional game art level, official character aesthetic, "
    "high quality anime game illustration, masterpiece character art"
)
cats["zaxiang_sfw"]["loras"]["佩可莉姆"]["negative_prompt"] = NEG_ANIME

cats["zaxiang_sfw"]["loras"]["凛酱"]["base_prompt"] = (
    "Rin anime character portrait, expressive anime face, "
    "detailed character costume design, same character identity preserved, "
    "professional anime illustration quality, clean sharp linework, "
    "character accurate faithful recreation, vibrant anime color, "
    "dynamic character pose optional, detailed hair and eye, "
    "anime game art standard, character portrait closeup, "
    "warm studio portrait lighting, professional illustration quality, "
    "accurate outfit and accessory, character fan art quality, "
    "clean anime rendering style, detailed character design, "
    "expressive eyes and expression, high quality anime illustration"
)
cats["zaxiang_sfw"]["loras"]["凛酱"]["negative_prompt"] = NEG_ANIME

cats["zaxiang_sfw"]["loras"]["复古CG风"]["base_prompt"] = (
    "retro early 2000s CGI aesthetic, vintage computer graphics render, "
    "PS2 era 3D graphic quality, old-school digital art nostalgia, "
    "blocky polygon low-res charm, early 3D game cutscene aesthetic, "
    "vintage Shrek or Final Fantasy CGI era, pre-HD 3D render quality, "
    "limited texture resolution charm, flat specular highlight, "
    "early 3D animation style, vintage render farm output, "
    "nostalgic digital art era, low polygon count aesthetic, "
    "early computer graphics texture map, Y2K digital aesthetic, "
    "pre-photorealism 3D style, classic CGI movie quality, "
    "retro digital art nostalgia, high quality retro CG render"
)
cats["zaxiang_sfw"]["loras"]["复古CG风"]["negative_prompt"] = NEG_3D

cats["zaxiang_sfw"]["loras"]["奥利维亚"]["base_prompt"] = (
    "Olivia anime character portrait, detailed character costume, "
    "same character identity preserved, professional anime illustration, "
    "clean sharp anime linework, accurate character design recreation, "
    "vibrant anime color palette, expressive eyes and face, "
    "detailed hair design, character accurate outfit, "
    "dynamic or idle character pose, warm portrait lighting, "
    "anime game art standard quality, detailed accessory, "
    "accurate character color scheme, fan art dedication quality, "
    "clean anime rendering, character closeup portrait, "
    "professional illustration detail, high quality anime art"
)
cats["zaxiang_sfw"]["loras"]["奥利维亚"]["negative_prompt"] = NEG_ANIME

cats["zaxiang_sfw"]["loras"]["排球服"]["base_prompt"] = (
    "volleyball sports uniform, tight-fitting jersey and shorts, "
    "volleyball team outfit, athletic sport figure, "
    "sports action dynamic pose, volleyball court background optional, "
    "clean sports jersey design, athletic confidence, "
    "volleyball player ready stance, sports photography quality, "
    "bright indoor arena lighting, competitive sport expression, "
    "detailed sports uniform fabric, kneepads optional, "
    "team color sports design, professional athlete aesthetic, "
    "authentic volleyball sport, energetic sport spirit, "
    "sports performance illustration, high quality sports art"
)
cats["zaxiang_sfw"]["loras"]["排球服"]["negative_prompt"] = NEG_SFW

cats["zaxiang_sfw"]["loras"]["无缝连体袜"]["base_prompt"] = (
    "seamless full-body sheer stockings, smooth tight-fitting bodysuit, "
    "sheer nylon or spandex material, form-fitting leotard design, "
    "seamless knit construction detail, body-contouring silhouette, "
    "smooth elastic fabric texture, subtle sheen on fabric, "
    "minimalist bodysuit aesthetic, clean simple lines, "
    "comfortable athletic or fashion wear, slim-fit body shape, "
    "neutral or black color palette, modern intimate apparel design, "
    "clean fashion photography, studio lighting, "
    "professional apparel fashion photography, detailed fabric texture, "
    "elegant body-hugging fit, high quality fashion illustration"
)
cats["zaxiang_sfw"]["loras"]["无缝连体袜"]["negative_prompt"] = NEG_SFW

cats["zaxiang_sfw"]["loras"]["泰国校服"]["base_prompt"] = (
    "Thai high school student uniform, crisp white button-down shirt, "
    "navy or plaid school skirt, school badge emblem, "
    "Thai school uniform style, student casual portrait, "
    "school setting background, neat clean uniform presentation, "
    "young student expression, school bag accessory optional, "
    "authentic Thai school fashion, school hallway or campus, "
    "clean pressed uniform fabric, student ID card optional, "
    "Southeast Asian school aesthetic, cheerful student expression, "
    "school uniform detail accuracy, natural portrait lighting, "
    "authentic school life photography, high quality portrait"
)
cats["zaxiang_sfw"]["loras"]["泰国校服"]["negative_prompt"] = NEG_REAL

cats["zaxiang_sfw"]["loras"]["漫画风"]["base_prompt"] = (
    "manga comic book style illustration, halftone screen tone patterns, "
    "bold clean ink outlines, black and white manga aesthetic, "
    "panel composition layout, speed line motion effect, "
    "manga expression and emotion, dot pattern screen tone shading, "
    "clean manga inking technique, classic shonen or shojo style, "
    "dramatic manga face closeup, manga panel border frame, "
    "speech bubble optional, sound effect lettering optional, "
    "traditional manga art quality, brush pen ink quality, "
    "weekly manga magazine aesthetic, authentic manga art tradition, "
    "high resolution manga scan quality, masterpiece manga art"
)
cats["zaxiang_sfw"]["loras"]["漫画风"]["negative_prompt"] = NEG_ANIME

cats["zaxiang_sfw"]["loras"]["牛仔啦啦队"]["base_prompt"] = (
    "denim cowboy western cheerleader outfit, blue denim mini skirt, "
    "denim jacket or crop top, pom-poms in hand, "
    "western cowboy hat accessory, country girl cheerleader aesthetic, "
    "cheerleading dynamic pose, western rodeo spirit, "
    "American country girl style, fringe denim detail, "
    "boots and cowgirl aesthetic, energetic cheerleader expression, "
    "denim patchwork design, bright cheerful colors, "
    "cheerleader squad formation optional, country music aesthetic, "
    "lively energetic performance, American western fashion, "
    "sports spirit illustration, high quality fashion illustration"
)
cats["zaxiang_sfw"]["loras"]["牛仔啦啦队"]["negative_prompt"] = NEG_SFW

cats["zaxiang_sfw"]["loras"]["玲珑"]["base_prompt"] = (
    "elegant slender refined figure, graceful delicate proportions, "
    "sophisticated poise and posture, refined feminine aesthetic, "
    "long slender limbs elegance, subtle sophisticated beauty, "
    "high-fashion model proportions, elongated graceful neck, "
    "minimalist elegant outfit, refined expression confidence, "
    "luxury fashion aesthetic, slender waist emphasis, "
    "artistic body proportion, architectural fashion pose, "
    "editorial fashion photography, clean aesthetic beauty, "
    "high couture elegance, natural confident grace, "
    "fashion illustration quality, high quality elegant portrait"
)
cats["zaxiang_sfw"]["loras"]["玲珑"]["negative_prompt"] = NEG_REAL

cats["zaxiang_sfw"]["loras"]["菱咲椎亚"]["base_prompt"] = (
    "Hishizaki Suia VTuber character, specific virtual YouTuber design, "
    "accurate character design recreation, anime VTuber aesthetic, "
    "detailed costume and accessory, expressive anime eyes, "
    "VTuber stream overlay aesthetic, accurate character color scheme, "
    "clean sharp anime illustration, character lore-accurate design, "
    "VTuber portrait closeup, warm studio virtual lighting, "
    "authentic VTuber character faithful art, professional anime art, "
    "detailed hair and outfit, accurate accessory recreation, "
    "fan art quality dedication, clean character illustration, "
    "expressive VTuber emotion, high quality anime VTuber art"
)
cats["zaxiang_sfw"]["loras"]["菱咲椎亚"]["negative_prompt"] = NEG_ANIME

cats["zaxiang_sfw"]["loras"]["蕾娜"]["base_prompt"] = (
    "Rena anime character portrait, specific character design recreation, "
    "accurate outfit and hair, expressive anime face detail, "
    "clean sharp anime illustration quality, character identity preserved, "
    "vibrant character color palette, detailed costume accuracy, "
    "character closeup portrait pose, warm portrait lighting, "
    "anime art professional quality, accurate accessory detail, "
    "fan art dedication quality, clean anime rendering, "
    "character lore-accurate design, dynamic or idle pose, "
    "professional anime illustration, expressive eyes, "
    "faithful character recreation, high quality anime portrait"
)
cats["zaxiang_sfw"]["loras"]["蕾娜"]["negative_prompt"] = NEG_ANIME

cats["zaxiang_sfw"]["loras"]["衣下内裤"]["base_prompt"] = (
    "panties visible beneath outer clothing, lifted skirt pose, "
    "underwear peek from under hem, coy playful expression, "
    "wind lifting skirt effect, casual clothing with lingerie accent, "
    "clean fashion photography, natural candid-like moment, "
    "delicate underwear fabric detail, cute fabric pattern, "
    "lifted dress or skirt dynamic, natural casual setting, "
    "clean composition photography, soft natural lighting, "
    "playful feminine aesthetic, fashionable outer clothing, "
    "intimate but tasteful expression, casual lifestyle portrait, "
    "authentic fashion photography quality, high quality portrait"
)
cats["zaxiang_sfw"]["loras"]["衣下内裤"]["negative_prompt"] = NEG_SFW

cats["zaxiang_sfw"]["loras"]["警察比基尼"]["base_prompt"] = (
    "sexy police officer costume bikini, cop hat and badge accessory, "
    "law enforcement themed outfit, revealing police-themed wear, "
    "handcuffs prop accessory, authority costume roleplay aesthetic, "
    "navy or black bikini with badge, playful cop character theme, "
    "confident powerful stance, themed costume detail accuracy, "
    "fashion costume photography, clean studio lighting, "
    "police officer visual elements, costume play aesthetic, "
    "professional fashion shoot quality, detailed costume accuracy, "
    "confident expression and pose, summer beach or studio setting, "
    "stylish costume concept, high quality fashion photography"
)
cats["zaxiang_sfw"]["loras"]["警察比基尼"]["negative_prompt"] = NEG_SFW

cats["zaxiang_sfw"]["loras"]["里斗风"]["base_prompt"] = (
    "Lidou dark web Chinese comic aesthetic, underground manga art style, "
    "dark gritty atmospheric art, dramatic high-contrast shadows, "
    "dark fantasy narrative composition, urban underground aesthetic, "
    "raw expressive ink quality, dark psychological atmosphere, "
    "Chinese dark web comic tradition, intense dramatic mood, "
    "detailed character with dark costume, gritty texture overlays, "
    "deep shadow color palette, intense expressive eyes, "
    "dark narrative visual storytelling, underground art culture, "
    "raw dramatic brushwork, forbidden aesthetic appeal, "
    "high intensity visual drama, high quality dark art"
)
cats["zaxiang_sfw"]["loras"]["里斗风"]["negative_prompt"] = NEG_ANIME

cats["zaxiang_sfw"]["loras"]["钢管舞"]["base_prompt"] = (
    "pole dance performance art, athletic pole dancer pose, "
    "dance studio pole installation, dynamic spinning aerial move, "
    "athletic flexibility and strength, pole dance routine position, "
    "dance studio mirror background, stage or club atmospheric lighting, "
    "costume appropriate for dance, confident performance expression, "
    "athletic muscular definition, graceful acrobatic balance, "
    "performance arts photography, dramatic stage lighting, "
    "pole grip and hold detail, dance choreography freeze-frame, "
    "professional dance photography, athletic performance art, "
    "expressive performance energy, high quality dance illustration"
)
cats["zaxiang_sfw"]["loras"]["钢管舞"]["negative_prompt"] = NEG_SFW

cats["zaxiang_sfw"]["loras"]["零度晚期风"]["base_prompt"] = (
    "zero degree terminal aesthetic, cold minimalist digital art, "
    "clinical antiseptic visual style, monochrome cool color palette, "
    "digital interface overlay elements, sterile medical or lab setting, "
    "frozen static composition, cyber-clinical aesthetic, "
    "cold blue-white light environment, diagnostic visual language, "
    "futurist minimalist design, data visualization element, "
    "late-stage futurism aesthetic, cold emotional distance, "
    "glitch artifact texture, terminal disease metaphor visual, "
    "flat clinical environment, stark contrast minimal composition, "
    "digital dystopia aesthetic, high quality cold digital art"
)
cats["zaxiang_sfw"]["loras"]["零度晚期风"]["negative_prompt"] = NEG_ANIME

cats["zaxiang_sfw"]["loras"]["逆阿尔法N"]["base_prompt"] = (
    "Reverse Alpha N character design, specific anime character recreation, "
    "accurate outfit and accessory detail, expressive anime portrait, "
    "character identity preserved, clean sharp anime linework, "
    "vibrant character color palette, detailed costume accuracy, "
    "character lore-accurate design, dynamic pose optional, "
    "warm studio lighting portrait, anime art professional quality, "
    "fan art dedication quality, clean anime rendering style, "
    "character accurate hair and eyes, authentic character recreation, "
    "professional anime illustration, detailed background optional, "
    "expressive anime character, high quality anime portrait"
)
cats["zaxiang_sfw"]["loras"]["逆阿尔法N"]["negative_prompt"] = NEG_ANIME

cats["zaxiang_sfw"]["loras"]["腋下"]["base_prompt"] = (
    "raised arm underarm pose, arm lifted above head, "
    "sleeveless or short-sleeve outfit, natural arm-raised posture, "
    "casual stretching pose, studio or natural background, "
    "clean natural body photography, confident relaxed expression, "
    "summer light clothing, natural arm extension, "
    "candid lifestyle portrait, soft natural lighting, "
    "clean composition photography, authentic body positive pose, "
    "casual fashion aesthetic, natural human movement, "
    "lifestyle portrait photography, authentic casual moment, "
    "clean artistic body portrait, high quality lifestyle photography"
)
cats["zaxiang_sfw"]["loras"]["腋下"]["negative_prompt"] = NEG_SFW

# ─────────────────────────────────────────────────────────────────────────────
# zaxiang_r18 category
# ─────────────────────────────────────────────────────────────────────────────
NEG_R18_FULL = ("censored, mosaic, black bar, pixelated genitals, blurry, "
                "bad anatomy, deformed, extra limbs, missing limbs, "
                "watermark, text overlay, logo, low quality, artifacts, "
                "grainy, overexposed, flat lighting, ugly, poorly drawn, "
                "bad proportions, out of frame, cut off limbs")

cats["zaxiang_r18"]["loras"]["R18手办风"]["base_prompt"] = (
    "adult R18 collectible figurine, nude figure sculpture style, "
    "erotic PVC adult figure, explicit figurine pose, "
    "detailed body sculpt, smooth skin-like material, "
    "professional adult figure photography, white studio background, "
    "accurate body proportion, nude female figure art, "
    "premium adult collector figurine, detailed erotic sculpt, "
    "nsfw figurine display pose, collector adult art quality, "
    "female anatomy accurate sculpt, adult art figurine, "
    "detailed private area sculpt, professional studio lighting, "
    "collector grade adult figure, high quality nsfw figurine"
)
cats["zaxiang_r18"]["loras"]["R18手办风"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["SM情侣"]["base_prompt"] = (
    "BDSM bondage couple, dominant and submissive dynamic, "
    "rope bondage shibari, leather restraint accessories, "
    "collar and leash detail, explicit SM erotic scene, "
    "powerful dominant expression, submissive vulnerable pose, "
    "nsfw explicit content, detailed bondage equipment, "
    "dungeon or bedroom setting, dramatic contrast lighting, "
    "fetish costume detail, SM power exchange dynamic, "
    "explicit erotic composition, adult BDSM art quality, "
    "accurate bondage knot detail, fetish fantasy scene, "
    "high quality nsfw illustration"
)
cats["zaxiang_r18"]["loras"]["SM情侣"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["上身裸露"]["base_prompt"] = (
    "topless female nude, bare chest exposed, naked upper body, "
    "natural bare breasts, nude portrait photography style, "
    "tasteful nude fine art quality, natural body confidence, "
    "warm soft studio lighting on skin, skin texture and detail, "
    "natural nipple and areola detail, tasteful boudoir aesthetic, "
    "subsurface scattering skin, fine art nude composition, "
    "figure study nude pose, intimate warm lighting, "
    "natural undressed confidence, classical nude art influence, "
    "detailed skin highlight and shadow, authentic figure nude, "
    "nsfw explicit nudity, high quality nude art photography"
)
cats["zaxiang_r18"]["loras"]["上身裸露"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["乳头吸吮"]["base_prompt"] = (
    "mouth on nipple oral stimulation, nipple sucking close-up, "
    "lips wrapped around nipple, wet tongue nipple lick, "
    "erotic breast play detail, explicit nipple oral action, "
    "close-up intimate view, saliva gloss wet detail, "
    "aroused nipple erect detail, sensual oral stimulation, "
    "partner intimate moment, explicit nsfw breast oral, "
    "detailed mouth and breast anatomy, erotic close-up composition, "
    "explicit intimate adult content, nsfw oral breast scene, "
    "high detail intimate closeup, adult explicit quality, "
    "accurate anatomy detail, high quality nsfw illustration"
)
cats["zaxiang_r18"]["loras"]["乳头吸吮"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["乳头拉扯"]["base_prompt"] = (
    "nipple pulling stretch erotic, fingers gripping and stretching nipple, "
    "breast nipple distension, erotic nipple torture play, "
    "explicit nipple manipulation detail, breast deformation stretch, "
    "nsfw nipple bdsm play, erotic pain pleasure expression, "
    "detailed breast and nipple anatomy, nipple elongation stretch, "
    "explicit adult breast play, intimate nsfw close-up, "
    "erotic expression during play, finger and nipple detail, "
    "breast sensitivity play, nsfw explicit adult content, "
    "detailed intimate anatomy, adult erotic quality, "
    "accurate anatomy explicit, high quality nsfw illustration"
)
cats["zaxiang_r18"]["loras"]["乳头拉扯"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["乳头链"]["base_prompt"] = (
    "nipple chain jewelry accessory, metal chain linking nipples, "
    "decorative nipple piercing jewelry, erotic body jewelry, "
    "nsfw body adornment detail, metal chain drape on chest, "
    "nipple clamp chain detail, bdsm accessory on breast, "
    "decorative chest jewelry composition, shiny metal chain detail, "
    "explicit adult body jewelry, tasteful nsfw adornment, "
    "detailed metal chain texture, intimate jewelry close-up, "
    "erotic body decoration, adult fetish accessory, "
    "jewelry and skin contrast, nsfw intimate composition, "
    "accurate jewelry anatomy, high quality nsfw illustration"
)
cats["zaxiang_r18"]["loras"]["乳头链"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["乳房下垂"]["base_prompt"] = (
    "natural saggy breasts nude, realistic hanging breast shape, "
    "natural breast weight and drape, mature natural body form, "
    "authentic breast anatomy gravity, natural nipple pointing down, "
    "mature female figure study, natural body positive nudity, "
    "fine art nude natural body, realistic breast anatomy, "
    "warm studio lighting on skin, natural undressed figure, "
    "authentic natural body shape, no implants natural sag, "
    "mature body nude art, natural breast texture detail, "
    "figure study natural anatomy, nsfw explicit nude, "
    "authentic body representation, high quality nsfw nude art"
)
cats["zaxiang_r18"]["loras"]["乳房下垂"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["俯视后入"]["base_prompt"] = (
    "doggy style sex position from above pov, rear penetration overhead angle, "
    "bird's-eye view sex scene, penetration from behind top-down, "
    "explicit doggy style intercourse, aerial angle sexual composition, "
    "vaginal penetration rear view, nsfw explicit sex scene, "
    "accurate sexual anatomy, partner on all fours position, "
    "explicit penetration visible, overhead camera angle, "
    "detailed sexual anatomy accuracy, adult explicit content, "
    "nsfw intercourse illustration, passionate sex scene, "
    "explicit adult content quality, accurate body proportion, "
    "detailed explicit scene, high quality nsfw illustration"
)
cats["zaxiang_r18"]["loras"]["俯视后入"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["单臂遮胸"]["base_prompt"] = (
    "one arm covering bare chest pose, topless arm-modesty nude, "
    "coy arm-covering breast gesture, nude with partial concealment, "
    "arm pressed against bare chest, shy innocent topless expression, "
    "tasteful nude modesty pose, natural bare upper body covered, "
    "delicate arm-over-chest composition, subtle nsfw nudity, "
    "boudoir photography tasteful, arm detail and bare skin, "
    "playful shy expression, natural lighting on skin, "
    "classic nude modesty pose, intimate self-covering gesture, "
    "fine art tasteful nudity, nsfw partial nude, "
    "elegant intimate composition, high quality nude portrait"
)
cats["zaxiang_r18"]["loras"]["单臂遮胸"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["即将插入"]["base_prompt"] = (
    "pre-insertion erotic moment, penis positioned near vagina, "
    "about to penetrate erotic scene, anticipation intimate moment, "
    "explicit genitalia close proximity, sex foreplay final stage, "
    "nsfw explicit pre-sex scene, erect penis near vulva, "
    "aroused genitalia detail, explicit adult content, "
    "intimate erotic anticipation, detailed sexual anatomy, "
    "nsfw explicit close-up, adult erotic art quality, "
    "accurate anatomy explicit, pre-coitus erotic moment, "
    "high tension erotic scene, nsfw adult illustration, "
    "detailed intimate anatomy, high quality nsfw art"
)
cats["zaxiang_r18"]["loras"]["即将插入"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["双端插入"]["base_prompt"] = (
    "double penetration sex scene, simultaneous vaginal and anal penetration, "
    "DP explicit adult content, two penis double insertion, "
    "triple conjunction explicit, nsfw explicit DP scene, "
    "accurate anatomical detail, dual penetration sex position, "
    "explicit nsfw adult content, detailed intimate anatomy, "
    "two males one female explicit, penetration accuracy anatomy, "
    "adult explicit composition, nsfw hardcore content, "
    "explicit sexual act detail, adult content quality, "
    "accurate body proportion, detailed explicit scene, "
    "nsfw adult illustration, high quality explicit art"
)
cats["zaxiang_r18"]["loras"]["双端插入"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["外射私处"]["base_prompt"] = (
    "external ejaculation on vulva, cumshot on pussy, "
    "semen on female genitalia, external cum shot detail, "
    "nsfw explicit ejaculation scene, cum dripping on vulva, "
    "explicit external climax, semen fluid detail, "
    "creampie external variant, detailed genital anatomy, "
    "explicit nsfw adult content, ejaculation close-up, "
    "adult explicit composition, accurate anatomy, "
    "nsfw explicit cum shot, adult art quality, "
    "explicit genital detail, cum texture detail, "
    "nsfw explicit illustration, high quality adult art"
)
cats["zaxiang_r18"]["loras"]["外射私处"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["多男爱抚"]["base_prompt"] = (
    "multiple males groping one female, group fondling explicit scene, "
    "gangbang fondling situation, many hands on female body, "
    "male group pleasure female, explicit group sexual scene, "
    "nsfw explicit group content, multiple male hands detail, "
    "female surrounded by males, group erotic scene composition, "
    "explicit adult group content, gangbang preliminary scene, "
    "accurate anatomy in group, explicit nsfw composition, "
    "adult group content quality, multiple interaction detail, "
    "nsfw adult explicit scene, detailed explicit anatomy, "
    "adult explicit illustration, high quality nsfw group art"
)
cats["zaxiang_r18"]["loras"]["多男爱抚"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["大量射精"]["base_prompt"] = (
    "massive ejaculation cumshot, excessive semen volume, "
    "cum overflow dripping, large load ejaculation, "
    "abundant cum spray, extreme cum volume, "
    "nsfw explicit cumshot quantity, cum covering body, "
    "voluminous semen texture detail, explicit climax scene, "
    "adult explicit content, cum flood composition, "
    "nsfw explicit ejaculation, detailed semen fluid, "
    "extreme cum quantity scene, adult art explicit, "
    "cum drip and pool detail, nsfw explicit illustration, "
    "accurate cum fluid detail, high quality nsfw art"
)
cats["zaxiang_r18"]["loras"]["大量射精"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["寝取NTR"]["base_prompt"] = (
    "NTR netorare cuckold scene, partner stolen another man, "
    "cuckolding infidelity explicit, another male sex scene, "
    "NTR genre erotic fantasy, stolen girlfriend or wife scene, "
    "nsfw explicit NTR scenario, intimate betrayal scene, "
    "another man penetrating partner, NTR emotional and physical, "
    "explicit infidelity scene, adult NTR illustration, "
    "nsfw explicit NTR content, cuckold scenario detail, "
    "NTR genre accurate scene, explicit adult content, "
    "betrayal erotic scene, nsfw NTR illustration, "
    "accurate anatomy explicit, high quality NTR nsfw art"
)
cats["zaxiang_r18"]["loras"]["寝取NTR"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["开腿舔穴"]["base_prompt"] = (
    "cunnilingus oral sex explicit, tongue on vulva licking, "
    "legs spread wide open position, mouth on pussy oral, "
    "explicit pussy licking close-up, oral sex performed on female, "
    "tongue detail on labia, nsfw explicit cunnilingus, "
    "spread legs vulva exposure, oral pleasure intimate scene, "
    "detailed oral anatomy accuracy, nsfw explicit oral content, "
    "adult explicit composition, tongue and vulva detail, "
    "female pleasure oral scene, explicit nsfw content, "
    "accurate anatomical detail, adult oral explicit illustration, "
    "nsfw explicit oral art, high quality adult illustration"
)
cats["zaxiang_r18"]["loras"]["开腿舔穴"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["拉帕R18"]["base_prompt"] = (
    "Lapa character explicit R18, specific anime character nsfw, "
    "accurate character design in explicit scene, anime R18 illustration, "
    "character identity preserved in adult scene, nsfw explicit pose, "
    "detailed character outfit partially removed, adult explicit content, "
    "accurate character anatomy, nsfw anime explicit illustration, "
    "character lore-accurate nsfw, adult fan art quality, "
    "explicit character scene detail, nsfw adult composition, "
    "anime explicit art quality, detailed nsfw scene, "
    "adult explicit illustration, nsfw character art, "
    "accurate explicit anatomy, high quality nsfw anime art"
)
cats["zaxiang_r18"]["loras"]["拉帕R18"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["男性自慰"]["base_prompt"] = (
    "male solo masturbation explicit, hand gripping erect penis, "
    "male self pleasure close-up, solo male masturbation scene, "
    "erect penis hand job solo, male genital detail explicit, "
    "nsfw solo male explicit content, masturbation gesture detail, "
    "erect penis anatomy accurate, male pleasure solo scene, "
    "explicit solo adult content, nsfw male explicit illustration, "
    "penis grip detail accuracy, adult male solo art, "
    "nsfw explicit male content, masturbation explicit scene, "
    "detailed male anatomy, accurate explicit content, "
    "nsfw adult male illustration, high quality nsfw art"
)
cats["zaxiang_r18"]["loras"]["男性自慰"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["翻折体位"]["base_prompt"] = (
    "mating press sex position, legs folded over head extreme, "
    "pile driver position explicit, legs pressed to chest sex, "
    "extreme flexibility sex position, missionary folded legs, "
    "nsfw explicit mating press, deep penetration position, "
    "legs over shoulders variant, female folded double penetration position, "
    "explicit extreme sex position, detailed anatomy accuracy, "
    "adult explicit position scene, nsfw hardcore content, "
    "explicit sex act detail, adult content quality, "
    "anatomically accurate explicit, detailed explicit scene, "
    "nsfw adult illustration, high quality explicit nsfw art"
)
cats["zaxiang_r18"]["loras"]["翻折体位"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["腹部隆起"]["base_prompt"] = (
    "belly bulge visible from penetration, stomach distension from deep sex, "
    "womb internal bulge showing, cervix bulge outline on belly, "
    "deep penetration belly deformation, internal sex visible abdomen, "
    "explicit deep sex belly effect, stomach visible penis outline, "
    "nsfw explicit belly bulge, internal anatomy visible, "
    "deep penetration explicit scene, belly distension detail, "
    "explicit adult anatomical detail, nsfw belly content, "
    "accurate anatomy explicit, deep sex visible effect, "
    "adult explicit belly art, nsfw detailed scene, "
    "accurate explicit anatomy, high quality nsfw illustration"
)
cats["zaxiang_r18"]["loras"]["腹部隆起"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["腿夹腰"]["base_prompt"] = (
    "legs wrapped around waist sex, thighs gripping partner hips, "
    "leg lock sex position, legs crossed behind partner, "
    "missionary legs locked position, female legs hugging male waist, "
    "intimate leg grip detail, legs wrap hold explicit scene, "
    "nsfw leg lock sex content, thigh pressure on hips, "
    "explicit intimate position, accurate anatomy detail, "
    "adult explicit position, leg grip sex scene, "
    "nsfw explicit anatomy, adult content quality, "
    "detailed body interaction, explicit position illustration, "
    "nsfw adult scene, high quality explicit nsfw art"
)
cats["zaxiang_r18"]["loras"]["腿夹腰"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["避孕套"]["base_prompt"] = (
    "condom on erect penis detail, latex condom rolled on penis, "
    "safe sex condom use explicit, condom wrapper prop, "
    "condom application scene, latex material detail on penis, "
    "nsfw explicit condom sex, condom tip reservoir detail, "
    "erect penis wearing condom, responsible sex explicit content, "
    "condom texture and material, adult sex toy/safe sex prop, "
    "explicit condom anatomy, nsfw explicit safe sex, "
    "detailed condom material, adult explicit content, "
    "accurate anatomical detail, condom during intercourse, "
    "nsfw adult illustration, high quality nsfw art"
)
cats["zaxiang_r18"]["loras"]["避孕套"]["negative_prompt"] = NEG_R18_FULL

cats["zaxiang_r18"]["loras"]["黑塔R18"]["base_prompt"] = (
    "Herta Honkai Star Rail character explicit R18, "
    "accurate Herta character design in nsfw scene, "
    "white hair spider mech owner character, explicit adult scene, "
    "character identity preserved nsfw, anime game character explicit, "
    "Herta outfit partially removed explicit, adult explicit content, "
    "accurate Herta anatomy faithful, nsfw game character art, "
    "character lore-accurate nsfw scene, adult fan art quality, "
    "explicit character composition, nsfw adult illustration, "
    "anime explicit art quality, Herta explicit detail, "
    "adult explicit character art, nsfw game art, "
    "accurate explicit scene, high quality nsfw anime art"
)
cats["zaxiang_r18"]["loras"]["黑塔R18"]["negative_prompt"] = NEG_R18_FULL

# ─── Write back ──────────────────────────────────────────────────────────────
REG_PATH.write_text(json.dumps(reg, ensure_ascii=False, indent=2))
print("Done. Updated lora_registry.json with 20-term prompts.")

# Quick sanity check
total = 0
for cat_key, cat in cats.items():
    for lora_key, lora in cat["loras"].items():
        bp = lora.get("base_prompt") or cat.get("base_prompt", "")
        np_ = lora.get("negative_prompt") or cat.get("negative_prompt", "")
        bp_terms = len([t for t in bp.split(",") if t.strip()])
        np_terms = len([t for t in np_.split(",") if t.strip()])
        if bp_terms < 18 or np_terms < 14:
            print(f"  WARN {cat_key}/{lora_key}: pos={bp_terms} neg={np_terms}")
        total += 1
print(f"Checked {total} LoRAs.")
