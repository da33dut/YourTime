from PIL import Image, ImageDraw

def make_tray_icon(size=64):
    img = Image.new("RGB", (size, size), (0, 120, 215))
    d = ImageDraw.Draw(img)

    def S(x): 
        return int(x * size / 64)

    d.ellipse([S(6), S(6), S(58), S(58)], fill="white")
    d.ellipse([S(14), S(14), S(50), S(50)], fill=(0, 120, 215))
    d.rectangle([S(30), S(18), S(34), S(34)], fill="white")
    d.rectangle([S(30), S(30), S(44), S(34)], fill="white")

    return img

if __name__ == "__main__":
    sizes = [16, 24, 32, 48, 64, 128, 256]
    icons = [make_tray_icon(s) for s in sizes]

    ico_path = "tools\icon.ico"   
    icons[0].save(
        ico_path,
        format="ICO",
        sizes=[(i.width, i.height) for i in icons],
        append_images=icons[1:],
    )
    print("ICO written", ico_path)
