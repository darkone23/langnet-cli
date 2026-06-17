<script lang="ts">
	type Variant = 'beast' | 'canonArch' | 'vineInitial';
	type Scale = 'sm' | 'md' | 'lg';

	type Props = {
		variant?: Variant;
		scale?: Scale;
		label?: string;
	};

	let { variant = 'beast', scale = 'md', label = 'Illuminated manuscript ornament' }: Props =
		$props();
</script>

<figure
	class:beast={variant === 'beast'}
	class:canon-arch={variant === 'canonArch'}
	class:vine-initial={variant === 'vineInitial'}
	class:sm={scale === 'sm'}
	class:lg={scale === 'lg'}
	class="orion-illuminated-sprite"
	data-artboard={variant}
	aria-label={label}
>
	{#if variant === 'beast'}
		<svg viewBox="0 0 190 140" preserveAspectRatio="xMidYMid meet" role="img" aria-hidden="true">
			<path class="construction-line" d="M42 112 L93 33 L148 112 Z M96 19 V128 M35 78 H166" />
			<circle class="construction-line" cx="95" cy="78" r="50" />
			<path class="construction-tick" d="M93 33 L86 45 M93 33 L101 45 M42 112 L54 108 M148 112 L136 108" />
			<path class="halo" d="M36 110 C36 70 58 39 91 34 C128 28 162 54 165 89 C168 122 134 132 88 125 C54 120 38 116 36 110 Z" />
			<path class="tail" d="M55 87 C31 82 21 60 34 42 C38 58 51 68 74 70 C48 67 41 82 55 87 Z" />
			<path class="body beast-body" d="M45 88 C46 55 72 36 103 39 C135 42 157 62 160 88 C164 119 125 132 78 121 C57 116 45 105 45 88 Z" />
			<path class="ear ear-a" d="M72 43 C64 24 76 15 91 34" />
			<path class="ear ear-b" d="M126 45 C136 27 123 16 106 37" />
			<path class="forelock" d="M94 39 C99 26 110 27 109 39 C114 29 127 32 122 45" />
			<circle class="eye eye-a" cx="84" cy="67" r="12.5" />
			<circle class="eye eye-b" cx="123" cy="68" r="12.5" />
			<circle class="spirit-glint glint-a" cx="88" cy="63" r="3.4" />
			<circle class="spirit-glint glint-b" cx="127" cy="64" r="3.4" />
			<g class="snoot">
				<path class="muzzle" d="M86 93 C96 87 116 87 126 94 C119 105 96 105 86 93 Z" />
				<path class="nose" d="M118 93 C124 94 127 98 123 102" />
				<path class="smile" d="M86 104 C99 112 118 112 131 103" />
			</g>
			<path class="paw paw-a" d="M57 118 C65 113 75 115 80 121 C72 126 62 125 57 118 Z" />
			<path class="paw paw-b" d="M126 121 C134 115 146 116 151 123 C143 128 132 128 126 121 Z" />
			<path class="foliate-ruff" d="M54 78 C43 72 38 82 49 88 M63 52 C52 48 49 59 59 63 M139 52 C151 48 154 59 143 63 M156 84 C168 80 169 94 155 96" />
			<path class="sketch-line" d="M45 89 C47 52 73 32 104 36 C138 39 160 64 160 91 M56 111 C78 128 128 131 153 104" />
		</svg>
	{:else if variant === 'canonArch'}
		<svg viewBox="0 0 240 150" preserveAspectRatio="xMidYMid meet" role="img" aria-hidden="true">
			<path class="construction-line" d="M29 128 H211 M47 128 V66 M82 128 V51 M120 128 V45 M158 128 V51 M193 128 V66" />
			<path class="construction-line" d="M29 66 C31 29 209 29 211 66 M47 75 C52 51 188 51 193 75" />
			<circle class="construction-line" cx="120" cy="130" r="84" />
			<path class="construction-tick" d="M47 66 L40 74 M82 51 L75 60 M120 45 L113 54 M158 51 L165 60 M193 66 L200 74" />
			<path class="halo" d="M22 131 V61 C22 26 218 26 218 61 V131 Z" />
			<path class="parchment-fleck fleck-a" d="M35 135 C71 139 104 138 122 134 C151 128 184 131 211 136" />
			<path class="arch-shadow" d="M34 130 V67 C34 40 206 40 206 67 V130" />
			<path class="arch-line arch-top" d="M29 128 V64 C31 30 209 30 211 64 V128" />
			<path class="arch-line arch-inner" d="M47 128 V75 C52 52 188 52 193 75 V128" />
			<path class="arch-line arch-table" d="M29 128 H211" />
			<path class="column" d="M47 64 V128 M82 51 V128 M120 45 V128 M158 51 V128 M193 64 V128" />
			<path class="column-shade" d="M53 70 V123 M88 58 V123 M126 52 V123 M164 58 V123 M199 70 V123" />
			<path class="spandrel" d="M48 66 C59 55 70 52 82 51 M83 51 C94 45 108 43 120 45 M120 45 C133 43 147 45 157 51 M158 51 C171 52 182 55 192 66" />
			<path class="rubric-line" d="M62 81 H103 M137 81 H178 M62 96 H103 M137 96 H178 M62 111 H103 M137 111 H178" />
			<path class="hatching" d="M38 73 L46 66 M38 88 L46 81 M38 103 L46 96 M195 73 L203 66 M195 88 L203 81 M195 103 L203 96" />
			<path class="canon-script script-a" d="M66 70 H98 M141 70 H171" />
			<path class="canon-script script-b" d="M67 88 H101 M141 88 H175" />
			<path class="canon-script script-c" d="M67 104 H95 M141 104 H169" />
			<circle class="rubric rubric-a" cx="58" cy="81" r="2.4" />
			<circle class="rubric rubric-b" cx="183" cy="96" r="2.4" />
			<circle class="rubric rubric-c" cx="58" cy="111" r="2.4" />
			<path class="cap cap-a" d="M39 64 H56 M73 51 H91 M111 45 H129 M149 51 H167 M184 64 H201" />
			<path class="knot" d="M35 35 C45 25 56 35 46 46 C35 57 24 46 35 35 Z M194 35 C204 25 215 35 205 46 C194 57 183 46 194 35 Z" />
			<path class="foliate-ruff" d="M35 35 C28 29 21 34 25 41 M46 46 C51 54 61 51 58 42 M194 35 C187 29 180 34 184 41 M205 46 C210 54 220 51 217 42" />
			<path class="gold-trace" d="M29 128 V64 C31 30 209 30 211 64 V128" />
		</svg>
	{:else}
		<svg viewBox="0 0 150 150" preserveAspectRatio="xMidYMid meet" role="img" aria-hidden="true">
			<path class="construction-line" d="M75 18 V132 M24 82 H132 M36 120 H63 M96 120 H126" />
			<circle class="construction-line" cx="76" cy="75" r="48" />
			<path class="construction-tick" d="M35 118 L47 111 M63 120 L58 108 M96 120 L102 108 M126 118 L114 111 M75 18 L68 30 M75 18 L82 30" />
			<path class="parchment-fleck fleck-a" d="M31 137 C49 142 74 142 94 136" />
			<path class="initial-stem" d="M25 121 H62 M94 121 H131" />
			<path
				class="initial-bowl"
				d="M40 119 C23 100 23 62 42 40 C61 18 98 21 116 43 C134 64 132 100 111 119 M57 111 C43 94 43 66 58 51 C72 37 94 39 106 55 C118 72 115 97 96 111"
			/>
			<path class="letter-shadow" d="M48 111 C35 93 35 65 50 46 C65 29 94 30 110 49" />
			<path class="initial-highlight" d="M61 103 C53 88 55 66 66 55 C78 44 96 47 105 61" />
			<path class="inhabited-head" d="M79 78 C88 68 104 72 106 86 C108 99 92 105 81 95 C76 90 75 83 79 78 Z" />
			<circle class="inhabited-eye eye-a" cx="88" cy="83" r="1.9" />
			<circle class="inhabited-eye eye-b" cx="100" cy="86" r="1.7" />
			<path class="inhabited-face" d="M87 94 C92 97 100 96 103 92" />
			<path class="vine vine-main" d="M38 113 C54 102 61 84 78 67 C94 52 110 60 119 78" />
			<path class="vine vine-tail" d="M38 52 C23 45 26 30 46 25" />
			<path class="leaf leaf-a" d="M78 65 C70 48 84 38 99 44 C98 58 90 66 78 65 Z" />
			<path class="leaf leaf-b" d="M119 78 C134 65 144 78 136 92 C126 93 119 88 119 78 Z" />
			<path class="leaf leaf-c" d="M39 52 C22 61 13 49 18 35 C31 35 39 42 39 52 Z" />
			<path class="foliate-ruff" d="M53 34 C62 39 61 49 53 55 M98 37 C109 42 111 55 100 61 M95 79 C106 86 106 102 95 110 M54 91 C64 98 63 111 52 118" />
			<path class="leaf-vein" d="M80 62 L96 44 M120 80 L137 88 M38 50 L18 35" />
			<path class="hatching" d="M39 103 C50 120 83 123 103 105 M43 47 C57 34 84 31 100 45" />
			<path class="knot" d="M67 21 C78 10 91 21 80 33 C68 45 55 33 67 21 Z" />
			<circle class="rubric rubric-a" cx="39" cy="23" r="3.2" />
			<circle class="rubric rubric-b" cx="94" cy="68" r="2.4" />
			<circle class="rubric rubric-c" cx="39" cy="127" r="3.2" />
		</svg>
	{/if}
</figure>

<style>
	.orion-illuminated-sprite {
		--sprite-size: 5.5rem;
		--sprite-ink: color-mix(in oklab, var(--reader-ornament-ink) 86%, var(--color-base-content));
		--sprite-gold: color-mix(in oklab, var(--reader-ornament-gold) 92%, var(--color-accent));
		--sprite-blue: color-mix(in oklab, var(--color-secondary) 78%, var(--reader-ornament-gold));
		--sprite-paper: color-mix(in oklab, var(--color-base-100) 78%, var(--reader-ornament-gold) 12%);
		--sprite-wash: color-mix(in oklab, var(--sprite-paper) 70%, transparent);
		position: relative;
		display: block;
		width: var(--sprite-size);
		max-width: 100%;
		max-height: 100%;
		height: var(--sprite-size);
		margin: 0;
		pointer-events: none;
		color: var(--sprite-ink);
		opacity: 0.9;
	}

	.orion-illuminated-sprite *,
	.orion-illuminated-sprite *::before,
	.orion-illuminated-sprite *::after {
		transform-box: fill-box;
	}

	.orion-illuminated-sprite.sm {
		--sprite-size: 3.8rem;
	}

	.orion-illuminated-sprite.lg {
		--sprite-size: 7.4rem;
	}

	.orion-illuminated-sprite.canon-arch {
		--sprite-size: 5.6rem;
		aspect-ratio: 240 / 150;
		height: auto;
	}

	.orion-illuminated-sprite.canon-arch.sm {
		--sprite-size: 4.1rem;
	}

	.orion-illuminated-sprite.canon-arch.lg {
		--sprite-size: min(6.8rem, 100%);
	}

	.orion-illuminated-sprite.vine-initial {
		--sprite-size: 5.1rem;
	}

	.orion-illuminated-sprite.vine-initial.sm {
		--sprite-size: 3.8rem;
	}

	.orion-illuminated-sprite.vine-initial.lg {
		--sprite-size: min(5.45rem, 100%);
	}

	.orion-illuminated-sprite.beast {
		--sprite-size: 5.35rem;
	}

	.orion-illuminated-sprite.beast.sm {
		--sprite-size: 4.05rem;
	}

	.orion-illuminated-sprite.beast.lg {
		--sprite-size: min(6.8rem, 100%);
	}

	.orion-illuminated-sprite svg {
		display: block;
		width: 100%;
		height: 100%;
		overflow: visible;
		filter: drop-shadow(0 0.22rem 0.32rem color-mix(in oklab, var(--color-neutral) 9%, transparent));
	}

	.orion-illuminated-sprite:not(.lg) .construction-line,
	.orion-illuminated-sprite:not(.lg) .construction-tick,
	.orion-illuminated-sprite:not(.lg) .sketch-line,
	.orion-illuminated-sprite:not(.lg) .halo,
	.orion-illuminated-sprite.beast .construction-line,
	.orion-illuminated-sprite.beast .construction-tick,
	.orion-illuminated-sprite.beast .sketch-line,
	.orion-illuminated-sprite.beast .halo,
	.orion-illuminated-sprite.sm .halo,
	.orion-illuminated-sprite.sm .hatching,
	.orion-illuminated-sprite.sm .column-shade,
	.orion-illuminated-sprite.sm .spandrel,
	.orion-illuminated-sprite.sm .foliate-ruff,
	.orion-illuminated-sprite.sm .leaf-vein,
	.orion-illuminated-sprite.sm .letter-shadow,
	.orion-illuminated-sprite.sm .initial-highlight,
	.orion-illuminated-sprite.sm .parchment-fleck,
	.orion-illuminated-sprite.sm .gold-trace {
		display: none;
	}

	.construction-line {
		fill: none;
		stroke: color-mix(in oklab, var(--sprite-blue) 38%, transparent);
		stroke-dasharray: 3 5;
		stroke-linecap: round;
		stroke-linejoin: round;
		stroke-width: 0.8;
		opacity: 0.34;
	}

	.construction-tick {
		fill: none;
		stroke: color-mix(in oklab, var(--sprite-blue) 42%, transparent);
		stroke-linecap: round;
		stroke-width: 0.75;
		opacity: 0.38;
	}

	.body,
	.beast-body,
	.ear,
	.muzzle,
	.nose,
	.paw,
	.forelock,
	.foliate-ruff,
	.leaf,
	.knot,
	.halo,
	.arch-shadow {
		stroke: var(--sprite-ink);
		stroke-width: 2.25;
		stroke-linecap: round;
		stroke-linejoin: round;
	}

	.body,
	.beast-body,
	.initial-bowl,
	.halo {
		fill: var(--sprite-wash);
	}

	.beast .beast-body {
		fill: color-mix(in oklab, var(--sprite-paper) 44%, transparent);
	}

	.beast .muzzle {
		fill: color-mix(in oklab, var(--sprite-paper) 54%, transparent);
	}

	.beast .ear,
	.beast .tail {
		fill: color-mix(in oklab, var(--sprite-gold) 22%, transparent);
	}

	.spirit-glint {
		fill: color-mix(in oklab, var(--sprite-paper) 70%, white 22%);
	}

	.beast .smile {
		fill: none;
		stroke: color-mix(in oklab, var(--sprite-ink) 70%, transparent);
		stroke-linecap: round;
		stroke-width: 1.35;
	}

	.beast .forelock,
	.beast .nose {
		fill: none;
		stroke: color-mix(in oklab, var(--sprite-ink) 82%, transparent);
		stroke-linecap: round;
		stroke-linejoin: round;
		stroke-width: 1.85;
	}

	.beast .muzzle {
		stroke-width: 2.05;
	}

	.beast .beast-body,
	.beast .tail,
	.beast .paw {
		stroke-width: 2.65;
	}

	.canon-arch .arch-line,
	.canon-arch .column,
	.vine-initial .initial-stem,
	.vine-initial .initial-bowl {
		stroke-width: 3.05;
	}

	.canon-arch .rubric-line,
	.canon-arch .canon-script {
		stroke-width: 1.45;
		opacity: 0.78;
	}

	.vine-initial .inhabited-head {
		opacity: 0.78;
		stroke-width: 1.45;
	}

	.vine-initial .inhabited-eye,
	.vine-initial .inhabited-face {
		opacity: 0.82;
	}

	.foliate-ruff,
	.sketch-line {
		fill: none;
		stroke: color-mix(in oklab, var(--sprite-ink) 74%, transparent);
		stroke-linecap: round;
		stroke-linejoin: round;
		stroke-width: 1.25;
	}

	.sketch-line {
		opacity: 0.44;
		stroke-width: 0.85;
	}

	.arch-shadow {
		fill: none;
		opacity: 0.18;
		stroke: var(--sprite-gold);
		stroke-width: 3.8;
	}

	.leaf-a,
	.leaf-c,
	.knot {
		fill: color-mix(in oklab, var(--sprite-gold) 24%, var(--sprite-paper));
	}

	.leaf-b {
		fill: color-mix(in oklab, var(--sprite-blue) 18%, var(--sprite-paper));
	}

	.paw {
		fill: color-mix(in oklab, var(--sprite-paper) 54%, transparent);
	}

	.eye,
	.inhabited-eye,
	.rubric {
		fill: var(--sprite-ink);
	}

	.inhabited-head {
		fill: color-mix(in oklab, var(--sprite-paper) 50%, transparent);
		stroke: var(--sprite-ink);
		stroke-linecap: round;
		stroke-linejoin: round;
		stroke-width: 1.5;
	}

	.inhabited-face {
		fill: none;
		stroke: color-mix(in oklab, var(--sprite-ink) 72%, transparent);
		stroke-linecap: round;
		stroke-width: 1.1;
	}

	.rubric {
		fill: color-mix(in oklab, var(--reader-ornament-ink) 86%, #d03020);
	}

	.vine,
	.hatching,
	.column-shade,
	.spandrel,
	.letter-shadow,
	.leaf-vein,
	.parchment-fleck,
	.arch-line,
	.column,
	.rubric-line,
	.canon-script,
	.cap,
	.initial-stem,
	.initial-bowl,
	.initial-highlight {
		fill: none;
		stroke: var(--sprite-ink);
		stroke-width: 1.9;
		stroke-linecap: round;
		stroke-linejoin: round;
	}

	.vine {
		stroke: color-mix(in oklab, var(--sprite-blue) 58%, var(--sprite-ink));
		stroke-width: 1.8;
	}

	.initial-highlight,
	.letter-shadow,
	.canon-script {
		stroke: color-mix(in oklab, var(--sprite-gold) 70%, var(--sprite-ink));
		stroke-width: 1.15;
		opacity: 0.62;
	}

	.letter-shadow {
		opacity: 0.42;
	}

	.leaf-vein,
	.column-shade,
	.spandrel {
		stroke: color-mix(in oklab, var(--sprite-ink) 58%, transparent);
		stroke-width: 0.9;
	}

	.hatching {
		stroke: color-mix(in oklab, var(--sprite-gold) 46%, var(--sprite-ink));
		stroke-width: 0.7;
		opacity: 0.34;
	}

	.parchment-fleck {
		stroke: color-mix(in oklab, var(--reader-ornament-gold) 48%, transparent);
		stroke-width: 0.95;
		opacity: 0.42;
	}

	.rubric-line,
	.cap {
		stroke: color-mix(in oklab, var(--sprite-gold) 78%, var(--sprite-ink));
		stroke-width: 1.55;
	}

	.arch-line,
	.column,
	.initial-stem,
	.initial-bowl {
		stroke-width: 2.65;
	}

	.gold-trace {
		fill: none;
		stroke: var(--sprite-gold);
		stroke-width: 1.15;
		stroke-linecap: round;
		stroke-dasharray: 430;
		stroke-dashoffset: 430;
		opacity: 0.8;
	}

	@media (prefers-reduced-motion: no-preference) {
		.beast svg {
			animation: orion-beast-attend 6.4s ease-in-out infinite;
			transform-origin: 50% 86%;
		}

		.beast .beast-body {
			animation: orion-spirit-breathe 6.8s ease-in-out infinite;
			transform-origin: 50% 70%;
		}

		.beast .eye {
			animation: orion-beast-blink 4.8s ease-in-out infinite;
			transform-origin: center;
		}

		.beast .tail {
			animation: orion-tail-curl 6.2s ease-in-out infinite;
			transform-origin: 44% 62%;
		}

		.beast .snoot {
			animation: orion-snoot-squash 5.8s ease-in-out infinite;
			transform-origin: center;
		}

		.beast .rubric {
			animation: orion-rubric-pulse 3.4s ease-in-out infinite;
		}

		.beast .vine-main,
		.construction-line {
			animation: orion-construction-breathe 7.8s ease-in-out infinite;
		}

		.sketch-line,
		.hatching {
			animation: orion-sketch-flicker 8.4s ease-in-out infinite;
		}

		.vine-initial .vine-main,
		.vine-initial .vine-tail {
			stroke-dasharray: 96;
			stroke-dashoffset: 96;
			animation: orion-vine-grow 4.6s ease-in-out infinite;
		}

		.vine-initial .rubric,
		.canon-arch .rubric {
			animation: orion-rubric-pulse 3.4s ease-in-out infinite;
		}

		.vine-initial .inhabited-head,
		.vine-initial .inhabited-eye,
		.vine-initial .inhabited-face {
			animation: orion-inhabitant-drift 10.5s ease-in-out infinite;
			transform-origin: 92px 88px;
		}

		.canon-arch .gold-trace {
			animation: orion-arch-trace 6.2s ease-in-out infinite;
		}

		.canon-arch .canon-script,
		.vine-initial .initial-highlight {
			stroke-dasharray: 72;
			stroke-dashoffset: 72;
			animation: orion-script-reveal 5.4s ease-in-out infinite;
		}

		.canon-arch .script-b {
			animation-delay: 180ms;
		}

		.canon-arch .script-c {
			animation-delay: 360ms;
		}

		.canon-arch .column {
			animation: orion-column-lift 7.2s ease-in-out infinite;
			transform-origin: 50% 100%;
		}

		.vine-initial .leaf {
			animation: orion-leaf-turn 5.2s ease-in-out infinite;
			transform-origin: center;
		}

		.vine-initial .leaf-b {
			animation-delay: 260ms;
		}

		.vine-initial .leaf-c {
			animation-delay: 520ms;
		}
	}

	@keyframes orion-beast-attend {
		0%,
		100% {
			transform: rotate(-1.5deg) translateY(0);
		}
		42% {
			transform: rotate(2.5deg) translateY(-0.16rem);
		}
		72% {
			transform: rotate(-0.4deg) translateY(0.04rem);
		}
	}

	@keyframes orion-plate-settle {
		0%,
		100% {
			transform: rotate(-0.45deg) translateY(0);
		}
		48% {
			transform: rotate(0.45deg) translateY(-0.04rem);
		}
	}

	@keyframes orion-beast-blink {
		0%,
		88%,
		100% {
			transform: scaleY(1);
		}
		92%,
		95% {
			transform: scaleY(0.18);
		}
	}

	@keyframes orion-wing-breathe {
		0%,
		100% {
			transform: rotate(0deg) scale(1);
		}
		46% {
			transform: rotate(-2deg) scale(1.025);
		}
	}

	@keyframes orion-spirit-breathe {
		0%,
		100% {
			transform: scale(1);
		}
		48% {
			transform: scale(1.022);
		}
	}

	@keyframes orion-tail-curl {
		0%,
		100% {
			transform: rotate(0deg);
		}
		52% {
			transform: rotate(-3.5deg);
		}
	}

	@keyframes orion-vine-grow {
		0% {
			stroke-dashoffset: 96;
			opacity: 0.55;
		}
		34%,
		76% {
			stroke-dashoffset: 0;
			opacity: 1;
		}
		100% {
			stroke-dashoffset: -96;
			opacity: 0.58;
		}
	}

	@keyframes orion-rubric-pulse {
		0%,
		100% {
			opacity: 0.62;
			transform: scale(0.92);
		}
		48% {
			opacity: 1;
			transform: scale(1.08);
		}
	}

	@keyframes orion-inhabitant-drift {
		0%,
		100% {
			opacity: 0.2;
			transform: translate(-0.16rem, 0.16rem) rotate(-7deg) scale(0.9);
		}

		18% {
			opacity: 0.84;
			transform: translate(0, 0) rotate(0deg) scale(1);
		}

		42% {
			opacity: 0.16;
			transform: translate(0.2rem, -0.14rem) rotate(8deg) scale(0.88);
		}

		62% {
			opacity: 0.78;
			transform: translate(0.08rem, 0.12rem) rotate(4deg) scale(0.98);
		}

		84% {
			opacity: 0.18;
			transform: translate(-0.12rem, -0.1rem) rotate(-5deg) scale(0.86);
		}
	}

	@keyframes orion-snoot-squash {
		0%,
		100% {
			transform: scaleX(1) scaleY(1);
		}

		38% {
			transform: scaleX(1) scaleY(1);
		}

		48% {
			transform: scaleX(1.16) scaleY(0.72);
		}

		58% {
			transform: scaleX(0.96) scaleY(1.04);
		}

		68% {
			transform: scaleX(1) scaleY(1);
		}
	}

	@keyframes orion-construction-breathe {
		0%,
		100% {
			opacity: 0.28;
		}
		48% {
			opacity: 0.48;
		}
	}

	@keyframes orion-sketch-flicker {
		0%,
		100% {
			opacity: 0.32;
		}
		54% {
			opacity: 0.55;
		}
	}

	@keyframes orion-arch-trace {
		0%,
		12% {
			stroke-dashoffset: 430;
		}
		46%,
		76% {
			stroke-dashoffset: 0;
		}
		100% {
			stroke-dashoffset: -430;
		}
	}

	@keyframes orion-script-reveal {
		0%,
		18% {
			stroke-dashoffset: 72;
			opacity: 0.32;
		}
		48%,
		80% {
			stroke-dashoffset: 0;
			opacity: 0.82;
		}
		100% {
			stroke-dashoffset: -72;
			opacity: 0.34;
		}
	}

	@keyframes orion-column-lift {
		0%,
		100% {
			transform: translateY(0);
			opacity: 0.92;
		}
		50% {
			transform: translateY(-0.04rem);
			opacity: 1;
		}
	}

	@keyframes orion-leaf-turn {
		0%,
		100% {
			transform: rotate(0deg) scale(1);
		}
		50% {
			transform: rotate(-4deg) scale(1.04);
		}
	}
</style>
