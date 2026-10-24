"""Choose Kuaishou's cover input via its visible action, including portal inputs."""
async def select_cover_file(page,modal,path):
    inputs=modal.locator('input[type="file"][accept*="image"]')
    if await inputs.count()==1:
        await inputs.set_input_files(str(path));return False
    actions=modal.get_by_text('上传图片',exact=True)
    visible=[actions.nth(i) for i in range(await actions.count()) if await actions.nth(i).is_visible()]
    if len(visible)!=1:
        raise RuntimeError('快手封面上传入口不唯一或不可用，未执行发布')
    async with page.expect_file_chooser(timeout=10000) as chooser:
        await visible[0].click(timeout=5000)
    await (await chooser.value).set_files(str(path))
    return True
