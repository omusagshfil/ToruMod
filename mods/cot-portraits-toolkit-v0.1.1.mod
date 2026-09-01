Replace:
}</style><script
With:
}
/* CoT Portraits Toolkit ---------------------------------------------------- */
/*                                                                            */
/* Originally based on Mellowben's DIY PC Portrait Mod. Although most of the  */
/* code was overhauled, the original idea is theirs.                          */
/*                                                                            */
/* Adds a custom portrait to the player's Character description and to        */
/* character's posts in Elkbook. The portrait can be chosen, changed, or      */
/* removed directly from the Character ui dialog and is stored with the       */
/* game's save data.                                                          */
/*                                                                            */
/* This version was made for KittyPatcher v0.1.5c. It may work with other     */
/* versions as well, but compatibility is not guaranteed.                     */
/* -------------------------------------------------------------------------- */

.pc-elkbook-portrait-anchor {
    position: relative;
    width: 60px;
    height: 60px;
}
.pc-elkbook-portrait {
    position: absolute;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    object-fit: cover;
    z-index: 1;
}

/* CSS class selectors */
/* Interaction widget elements */
.m-npc-portrait-basic-interaction-img {
    width: 200px;
    height: 200px;
    object-fit: cover;
}
.m-npc-portrait-basic-interaction-wrapper {
    float: left;
    min-height: 400px;
    margin-bottom: 0.5em;
}
@media (max-width: 535px) {
    .m-npc-portrait-basic-interaction-wrapper {
        float: none;
        min-height: 0;
    }
}
/* People Grid widget elements */
.m-npcportrait-basic-grid-img {
    width: 200px;
    height: 200px;
    object-fit: cover;
    margin: 0 0 0 20px;
}
.m-npcportrait-basic-grid-wrapper {
    position: relative;
}
/* NPC Sheet widget elements */
.m-npcportrait-basic-sheet-img {
    position: absolute;
    width: 80px;
    height: 80px;
    left: -40px;
    top: -40px;
    border-radius: 50%;
    object-fit: cover;
}
.m-npcportrait-basic-sheet-wrapper {
    position: relative;
}
/* Elkbook thumbnail widget elements */
.m-npcportrait-basic-elkbook-img {
    position: absolute;
    width: 60px;
    height: 60px;
    left: -30px;
    top: -30px;
    border-radius: 50%;
    object-fit: cover;
}
.m-npcportrait-basic-elkbook-wrapper {
    position: relative;
}

.portrait-description {
    float: none;
    margin: 0px 20px 0px 0px;
}
.portrait-button-icon {
    width: 18px;
    height: 18px;
    object-fit: contain;
    vertical-align: middle;
}
/* -------------------------------------------------------------------------- */

</style><script

Add Javascript:
/* -------------------------------------------------------------------------- */
/* Portrait initialization and persistence                                    */
/* -------------------------------------------------------------------------- */

function initPortraitMod() {

    /* The mod script is injected before SugarCube finishes initializing.
       Retry until the APIs used by the mod are available. */
    if (
        typeof setup === "undefined" ||
        typeof Save === "undefined" ||
        typeof State === "undefined"
    ) {
        setTimeout(initPortraitMod, 50);
        return;
    }

    /* Ensure the portrait collection exists. */
    if (!State.variables.mPortraits) {
        State.variables.mPortraits = {};
    }

    /* Store portraits separately in saves so changes made from dialogs
       are preserved even before the next passage change. */
    if (!setup.portraitPersistenceInitialized) {

        Save.onSave.add(function (save) {
            save.mPortraits = State.variables.mPortraits;
        });

        Save.onLoad.add(function (save) {
            if (save.mPortraits !== undefined) {
                save.state.history[save.state.index].variables.mPortraits =
                    save.mPortraits;
            }
        });

        setup.portraitPersistenceInitialized = true;
    }


    /* Refresh whichever dialog owns the portrait. */
    function refreshPortrait(portraitKey) {

        if (portraitKey === "PC") {

            Dialog.setup("Character", "character");
            Dialog.wiki(Story.get("Character").processText());
            Dialog.open();

        } else {

            Dialog.setup("View Person", "view-person");
            Dialog.wiki(Story.get("DisplayNPC").processText());
            Dialog.open();
        }
    }

    /* Load the selected image into the appropriate portrait slot. */
    $(document).on("change", ".m-portrait-picker", function () {

        const file = this.files[0];
        if (!file) return;

        const portraitKey = $(this).attr("data-portrait-key");
        if (!portraitKey) return;

        const reader = new FileReader();

        reader.onload = function (event) {

            const img = new Image();

            img.onload = function () {

                const size = 200;

                const canvas = document.createElement("canvas");
                canvas.width = size;
                canvas.height = size;

                const ctx = canvas.getContext("2d");

                const sourceSize = Math.min(
                    img.naturalWidth,
                    img.naturalHeight
                );

                const sourceX = (img.naturalWidth - sourceSize) / 2;
                const sourceY = (img.naturalHeight - sourceSize) / 2;

                ctx.drawImage(
                    img,
                    sourceX,
                    sourceY,
                    sourceSize,
                    sourceSize,
                    0,
                    0,
                    size,
                    size
                );

                /* Ensure the portrait collection exists. */
                if (!State.variables.mPortraits) {
                    State.variables.mPortraits = {};
                }

                State.variables.mPortraits[portraitKey] =
                    canvas.toDataURL("image/jpeg", 0.85);

                refreshPortrait(portraitKey);
            };

            img.src = event.target.result;
        };

        reader.readAsDataURL(file);
    });

    /* Remove the current portrait. */
    $(document).on("click", ".m-portrait-remove", function () {

        const portraitKey = $(this).attr("data-portrait-key");
        if (!portraitKey) return;

        if (State.variables.mPortraits) {
            delete State.variables.mPortraits[portraitKey];
        }

        $(".m-portrait-picker")
            .filter(function () {
                return $(this).attr("data-portrait-key") === portraitKey;
            })
            .val("");

        refreshPortrait(portraitKey);
    });

    /* Open the appropriate hidden native file picker. */
    $(document).on("click", ".m-portrait-choose", function () {

        const portraitKey = $(this).attr("data-portrait-key");
        if (!portraitKey) return;

        $(".m-portrait-picker")
            .filter(function () {
                return $(this).attr("data-portrait-key") === portraitKey;
            })
            .trigger("click");
    });

}

initPortraitMod();
/* -------------------------------------------------------------------------- */

Add Passage:
<tw-passagedata pid="888028" name="NPCPortraitWidgetsBasic" tags="widget nobr" position="880,880" size="100,100">
<e>
<<widget "m-npcportrait-basic-display">> /* Calls resolver and displays the portrait widget */
    <div @class="_wrapperClass">
        <<m-npcportrait-basic-resolve>> 
        <img @class="_imgClass" @src="_portraitPath">
    </div>
<</widget>>

<<widget "m-npcportrait-basic-resolve">> /* Resolves portrait path based on npc's characteristics */

    <<set _resFolder to "res/img/portraits-toolkit/">>

    <<if setup.people.is_anonymous(_portraitSource)>>
        <<set _portraitPath to _resFolder + "anon.png">>

    <<else>>
        <<set _npcData to setup.people.expand(_portraitSource)>>    
        <<set _npc to setup.people.get_person(_portraitSource)>>

        <<if def $mPortraits and $mPortraits[_npcData.person]>>            
            <<set _portraitPath to $mPortraits[_npcData.person]>>
        <<else>>

            <<set _age to _npcData.age>>
            <<set _skinColor to _npcData['skin color']>>
            <<set _gender to _npcData.gender>>
            <<set _style to _npcData.style.toLowerCase()>>

            <<set _masculineGenders to ["male", "nonbinary amab", "transgender male"]>>
            <<set _basicStyles to ["basic", "conservative"]>>
            <<set _formalStyles to ["formal", "business suit"]>>
            <<set _prepStyles to ["prep", "business casual", "law enforcement", "campus police", "medical", "delivery driver"]>>

            <<set _portraitFolder to (_age >= 40) ? _resFolder + "50/" : _resFolder + "20/">>

            <<set _normalizedStyle to _style>>
            <<if _basicStyles.includes(_style)>>
                <<set _normalizedStyle to "basic">>
            <<elseif _formalStyles.includes(_style)>>
                <<set _normalizedStyle to "formal">>
            <<elseif _prepStyles.includes(_style)>>
                <<set _normalizedStyle to "prep">>
            <</if>>

            <<set _genderSuffix to _masculineGenders.includes(_gender) ? "-m.png" : "-f.png">>

            <<set _skinTone to "olive">>
            <<if _skinColor is "pale" or _skinColor is "fair">>
                <<set _skinTone to "pale">>
            <<elseif _skinColor is "beige" or _skinColor is "gold-beige">>
                <<set _skinTone to "beige">>
            <<elseif _skinColor is "tan" or _skinColor is "light brown">>
                <<set _skinTone to "tan">>
            <<elseif _skinColor is "brown" or _skinColor is "dark brown" or _skinColor is "deep brown">>
                <<set _skinTone to "brown">>
            <</if>>

            <<set _portraitFilename to _skinTone + "-" + _normalizedStyle + _genderSuffix>>
            <<set _portraitPath to _portraitFolder + _portraitFilename>>
        <</if>>
    <</if>>
<</widget>>

<<widget "m-npcportrait-basic-interaction">> /* Sets up the interaction scene and calls the display widget */

    <<set _personobj to new Person({person: $eventnpc})>>
    <<set _portraitSource to _personobj>>
    <<set _wrapperClass to "m-npc-portrait-basic-interaction-wrapper">>
    <<set _imgClass to "m-npc-portrait-basic-interaction-img">>

    <<m-npcportrait-basic-display>>

<</widget>>
<<widget "m-npcportrait-basic-grid">> /* Sets up the people grid scene and calls the display widget */
    
    <<set _portraitSource to _displayperson>>
    <<set _wrapperClass to "m-npcportrait-basic-grid-wrapper">>
    <<set _imgClass to "m-npcportrait-basic-grid-img">>

    <<m-npcportrait-basic-display>>

<</widget>>
<<widget "m-npcportrait-basic-sheet">> /* Sets up the npc sheet scene and calls the display widget */
    
    <<set _portraitSource to _personobj>>
    <<set _wrapperClass to "m-npcportrait-basic-sheet-wrapper">>
    <<set _imgClass to "m-npcportrait-basic-sheet-img">>

    <<m-npcportrait-basic-display>>
    
<</widget>>
<<widget "m-npcportrait-basic-elkbook-profile">> /* Sets up the elkbook thumbnail in npc profiles and calls the display widget */

    <<set _npc to setup.people.expand(_target)>>
    <<set _portraitSource to _npc>>
    <<set _wrapperClass to "m-npcportrait-basic-elkbook-wrapper">>
    <<set _imgClass to "m-npcportrait-basic-elkbook-img">>

    <<m-npcportrait-basic-display>>

<</widget>>
<<widget "m-npcportrait-basic-elkbook-timeline">> /* Sets up the elkbook thumbnails in the timeline calls the display widget */

    <<set _npc to setup.people.expand(_name)>>
    <<set _portraitSource to _npc>>
    <<set _wrapperClass to "m-npcportrait-basic-elkbook-wrapper">>
    <<set _imgClass to "m-npcportrait-basic-elkbook-img">>

    <<m-npcportrait-basic-display>>

<</widget>>
<<widget "m-npcportrait-basic-elkbook-reactions">> /* Sets up the elkbook reactions thumbnails and calls the display widget */

    <<set _npc to setup.people.expand(_student)>>
    <<set _portraitSource to _npc>>
    <<set _wrapperClass to "m-npcportrait-basic-elkbook-wrapper">>
    <<set _imgClass to "m-npcportrait-basic-elkbook-img">>

    <<m-npcportrait-basic-display>>

<</widget>>

<<widget "m-portrait-controls">>

    <<set _portraitKey to _args[0]>>

    <<if $mPortraits and $mPortraits[_portraitKey]>>
        <div class="portrait-description">
            <img @src="$mPortraits[_portraitKey]">
        </div>
    <</if>>

    <input
        type="file"
        class="m-portrait-picker"
        accept="image/*"
        @data-portrait-key="_portraitKey"
        hidden
    >

    <button class="m-portrait-choose" @data-portrait-key="_portraitKey">
        <<if $mPortraits and $mPortraits[_portraitKey]>>
            <img src="res/img/portraits-toolkit/edit.png" class="portrait-button-icon">
        <<else>>
            <img src="res/img/portraits-toolkit/upload.png" class="portrait-button-icon">
        <</if>>
    </button>

    <<if $mPortraits and $mPortraits[_portraitKey]>>
        <button class="m-portrait-remove" @data-portrait-key="_portraitKey">
            <img src="res/img/portraits-toolkit/remove.png" class="portrait-button-icon">
        </button>
    <</if>>

    <br>
    <br>

<</widget>>
</e>
</tw-passagedata>

Replace:
            Your name is &lt;&lt;highlight&gt;&gt;$pcname&lt;&lt;/highlight&gt;&gt;&lt;&lt;if $pc.nickname isnot &quot;&quot;&gt;&gt;, or &lt;&lt;highlight&gt;&gt;&lt;&lt;= $pc.nickname&gt;&gt;&lt;&lt;/highlight&gt;&gt; to your friends&lt;&lt;/if&gt;&gt;.
With:
            /* PC portrait and controls in Character description */
            <e>
            <<m-portrait-controls "PC">>
            </e>

            Your name is &lt;&lt;highlight&gt;&gt;$pcname&lt;&lt;/highlight&gt;&gt;&lt;&lt;if $pc.nickname isnot &quot;&quot;&gt;&gt;, or &lt;&lt;highlight&gt;&gt;&lt;&lt;= $pc.nickname&gt;&gt;&lt;&lt;/highlight&gt;&gt; to your friends&lt;&lt;/if&gt;&gt;.

Replace:
            &lt;&lt;= setup.people.firstname($pc).charAt(0)&gt;&gt;&lt;&lt;= setup.people.lastname($pc).charAt(0)&gt;&gt;
With:
            /* Replace PC initials with portrait thumbnail when available */
            <e>
            <<if $mPortraits and $mPortraits["PC"]>>
                <div class="pc-elkbook-portrait-anchor">
                    <img @src="$mPortraits['PC']" class="pc-elkbook-portrait">
                </div>
            <<else>>
                <<= setup.people.firstname($pc).charAt(0)>><<= setup.people.lastname($pc).charAt(0)>>
            <</if>>
            </e>

Replace:
                    &lt;&lt;= setup.people.firstname(_student).charAt(0)&gt;&gt;&lt;&lt;= setup.people.lastname(_student).charAt(0)&gt;&gt;
With:
                    <e>
                    <<m-npcportrait-basic-elkbook-reactions>>
                    </e>

Replace:
                                &lt;&lt;= setup.people.firstname(_name).charAt(0)&gt;&gt;&lt;&lt;= setup.people.lastname(_name).charAt(0)&gt;&gt;
With:
                                <e>
                                <<m-npcportrait-basic-elkbook-timeline>>
                                </e>

Replace:
                    &lt;&lt;= setup.people.firstname(_target).charAt(0)&gt;&gt;&lt;&lt;= setup.people.lastname(_target).charAt(0)&gt;&gt;
With:
                    <e>
                    <<m-npcportrait-basic-elkbook-profile>>
                    </e>

Replace:

                        &lt;&lt;if _niche != null&gt;&gt;
                            &lt;div class=&quot;view-people-person-niche faded small&quot;&gt;
                                &lt;&lt;= _niche&gt;&gt;
                            &lt;/div&gt;
                        &lt;&lt;/if&gt;&gt;
With:
                        &lt;&lt;if _niche != null&gt;&gt;
                            &lt;div class=&quot;view-people-person-niche faded small&quot;&gt;
                                &lt;&lt;= _niche&gt;&gt;
                            &lt;/div&gt;
                        &lt;&lt;/if&gt;&gt;
                
                        <e>
                        <<m-npcportrait-basic-grid>>
                        </e>

Replace:
            &lt;div @class=&quot;_avclass&quot;&gt;
                &lt;&lt;if !_anon and _known&gt;&gt;
                    &lt;&lt;= _personobj.fullname().charAt(0)&gt;&gt;&lt;&lt;= _personobj.lastname().charAt(0)&gt;&gt;
                &lt;&lt;else&gt;&gt;
                    ??
                &lt;&lt;/if&gt;&gt;
            &lt;/div&gt;
With: 
            &lt;div @class=&quot;_avclass&quot;&gt;
        	<e>
        	<<m-npcportrait-basic-sheet>>
        	</e>
            &lt;/div&gt;

Replace:
<tw-passagedata pid="149" name="InPersonDialogueMenu" tags="noevents noclothingfix dialogue nobr" position="1100,1850" size="100,100">
With:
<tw-passagedata pid="149" name="InPersonDialogueMenu" tags="noevents noclothingfix dialogue nobr" position="1100,1850" size="100,100">
<e>
<<m-npcportrait-basic-interaction>>
</e>

Replace:
You look speculatively at &lt;&lt;anonorfirstname $eventnpc&gt;&gt;. How should you flirt with &lt;&lt;po&gt;&gt;?
&lt;br&gt;&lt;br&gt;
With:
You look speculatively at &lt;&lt;anonorfirstname $eventnpc&gt;&gt;. How should you flirt with &lt;&lt;po&gt;&gt;?
&lt;br&gt;&lt;br&gt;

<e>
<<m-npcportrait-basic-interaction>>
</e>


Replace:
&lt;br&gt;&lt;br&gt;

&lt;&lt;if !$profinteractionstoday[$eventnpc].includesAny([&quot;punish&quot;, &quot;abort&quot;])&gt;&gt;
With:
&lt;br&gt;&lt;br&gt;

<e>
<<m-npcportrait-basic-interaction>>
</e>

&lt;&lt;if !$profinteractionstoday[$eventnpc].includesAny([&quot;punish&quot;, &quot;abort&quot;])&gt;&gt;

Replace:
&lt;&lt;widget &quot;displaynpcdescription&quot;&gt;&gt;
With:
&lt;&lt;widget &quot;displaynpcdescription&quot;&gt;&gt;

    /* NPC portrait and controls in NPC description */
    <e>
    <<m-portrait-controls _personobj.person>>
    </e>