## Introduction
Blender add-on that lets you automatically build outfits for different body shapes.

Quick demo video


https://github.com/PerplexedPeach/outfit_builder/assets/48222967/4ca17361-6015-47ef-b07e-e08c4c2b195b

1.1 also allows manually specifying the body instead of using the first selected item

https://github.com/PerplexedPeach/outfit_builder/assets/48222967/e61b6084-235b-4f97-bd7a-fa143f2e8de4


## Installation
- download as zip (green button on the github page)
  
  ![2023-10-22 00_09_16-PerplexedPeach_outfit_builder_ Generate outfits for different body shapes](https://github.com/PerplexedPeach/outfit_builder/assets/48222967/f738daf3-5893-4c1f-82d4-c269e009a825)

- extract anywhere
- in Blender > Edit > Preferences > Add-ons > Install > navigate to and select outfit_builder.py

  ![2023-10-22 00_11_33-Blender File View](https://github.com/PerplexedPeach/outfit_builder/assets/48222967/45aceeae-9f63-4ec0-81c6-38db2274adb7)

- in the search bar of preferences, search for outfit and check Outfit Builder
![2023-10-22 00_12_34-Blender Preferences](https://github.com/PerplexedPeach/outfit_builder/assets/48222967/441c9063-882c-4f0b-8126-e461a6af0ba0)

You also need to install the free [Mesh Data Transfer add-on](https://mmemoli.gumroad.com/l/tOKEh) in a similar way

## Tutorial
After you enabled the add-on, you should see a new tab appear on the right of the 3D view

![2023-10-22 00_16_21-Blender  F__bg3 assets_all_body_armor blend](https://github.com/PerplexedPeach/outfit_builder/assets/48222967/521fb3ff-baf7-487e-954e-826648cc6e68)

**Important**: you need to have a body object with shapes defined as shape keys, as well as the armature enabled and visible. 
If you already have body shapes defined as separate meshes (such as by proportionally editing a copy of the body), you can load them as a shape key of the base mesh by multiselecting the shape mesh first, then the base mesh. The Mesh Data Transfer add-on can also be used to transfer and generate shape keys.

![2023-10-22 00_30_06-Window](https://github.com/PerplexedPeach/outfit_builder/assets/48222967/861b03b9-8810-4c94-806c-e599b144bf4d)

You then need to multiselect the body first, then a number of armor pieces. Since 1.1, you can also explicitly set the body (see video above). These should all belong to the same armature, so don't mix HUM_F and HUM_FS armor pieces, for example.
Then you **run the outfit builder** on them by pressing `Build Outfits` or pressing hotkeys `Shift` + `Ctrl` + `B`. 

The different options explained:
- Export: Whether to export to GR2, or to just generate the different mesh variants inside blender. You need to have the [dos2de collada exporter](https://github.com/Norbyte/dos2de_collada_exporter) add-on to actually export. Running it may freeze the blender UI for a while, but just wait. The name of the exported meshes will be `<body name>_<armor name>_<shape name>.GR2`
- Hide shapes after export: Whether to hide the shape variant meshes after generating them. This is only meaningful if you don't remove shapes after export.
- Remove shapes after export: Whether to remove the shape variant meshes after exporting them.
- Body Mesh: Explictly set the body to take the shape keys from. Necessary in certain cases where multi-selection does not let you select the body first.
- Output dir: Directory to export the GR2 files. If empty, the local directory of the blender file will be used.

## Weight Transfer Tips
When changing between body types and shapes (e.g. HUM_F to HUM_FS or HUM_M), you'll need to:
1. parent the armor mesh under the new armature (HUM_F and HUM_M use different armatures) by dragging the mesh to the armature and holding shift when dropping to set as parent
2. data transfer vertex weights
    - for HUM_M, just transfer the Chest_M key for best results
    - for HUM_FS, transfer over all weights (default behavior)


## Shape Key Tips
See the included template blender file for slim to strong shape keys. You can build similar ones for your custom body shapes.
Shape keys are used for body sliders and so on (can also be used in animations). There is a direct vertex ID mapping between slim and strong body variants, so you can get the strong variant as a shape key of the slim body easily by Mesh Data Transfer with vertex ID as the search method (see below)

![2023-10-22 13_14_07-Window](https://github.com/PerplexedPeach/outfit_builder/assets/48222967/b3985059-9a74-499f-831b-a90201b2f532)

## VisualBank (LSX) Generation
New in 1.2, you can now generate the VisualBank resources. You need to have a single VisualBank resource defined for your basis mesh. Select it in the LSX in under the VisualBank (LSX) Builder panel. You do not need to have any armor selected inside blender, but a body should be either be set or selected.

![image](https://github.com/PerplexedPeach/outfit_builder/assets/48222967/1f637c40-6adb-4722-86b8-865cf71be303)

Sample such LSX file (it needs to have suffix lsf.lsx). Only the basis mesh should be defined, and the Name should match the prefix of the filename. If the name ends with "_Basis" then that will be stripped (e.g. `HUM_F_LI_Nightsong_Basis` becomes `HUM_F_LI_Nightsong`).
![image](https://github.com/PerplexedPeach/outfit_builder/assets/48222967/267734a0-45ce-4eec-ac73-531d5ff643e9)

Clicking the Build Visual Bank will generate a file with the same filename as the input LSX but with a `_generated` suffix. One VisualBank resource will be generated per body shape key (except Basis) per VisualBank in the input file. Each one will have name `<name>_<shape key name>`, and already have a UUID generated.

![image](https://github.com/PerplexedPeach/outfit_builder/assets/48222967/9640f7fd-027c-413d-bcae-4d51d36a1c95)

![image](https://github.com/PerplexedPeach/outfit_builder/assets/48222967/18836e55-bd4b-44c2-aadc-8dc9a920ea04)

