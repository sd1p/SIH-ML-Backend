import torch
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torch.nn.functional as F
from PIL import Image
from labels import image_labels
import os
import sys

# sys.path.append("D:/VS_Code/Assignments/FastAPI/mainProj")
# model_path = r"D:\VS_Code\Assignments\FastAPI\mainProj\app\model\plant-disease-model-complete.pth"

absolute_path = os.path.dirname(__file__)
relative_model_path = "../model/plant-disease-model-complete.pth"
model_path = os.path.join(absolute_path, relative_model_path)


def accuracy(outputs, labels):
    _, preds = torch.max(outputs, dim=1)
    return torch.tensor(torch.sum(preds == labels).item() / len(preds))


# Architecture for training
class ImageClassificationBase(nn.Module):
    def training_step(self, batch):
        images, labels = batch
        out = self(images)  # Generate predictions
        loss = F.cross_entropy(out, labels)  # Calculate loss
        return loss

    def validation_step(self, batch):
        images, labels = batch
        out = self(images)  # Generate prediction
        loss = F.cross_entropy(out, labels)  # Calculate loss
        acc = accuracy(out, labels)  # Calculate accuracy
        return {"val_loss": loss.detach(), "val_accuracy": acc}

    def validation_epoch_end(self, outputs):
        batch_losses = [x["val_loss"] for x in outputs]
        batch_accuracy = [x["val_accuracy"] for x in outputs]
        epoch_loss = torch.stack(batch_losses).mean()  # Combine loss
        epoch_accuracy = torch.stack(batch_accuracy).mean()
        return {
            "val_loss": epoch_loss,
            "val_accuracy": epoch_accuracy,
        }  # Combine accuracies

    def epoch_end(self, epoch, result):
        print(
            "Epoch [{}], last_lr: {:.5f}, train_loss: {:.4f}, val_loss: {:.4f}, val_acc: {:.4f}".format(
                epoch,
                result["lrs"][-1],
                result["train_loss"],
                result["val_loss"],
                result["val_accuracy"],
            )
        )


# convolution block with BatchNormalization
def ConvBlock(in_channels, out_channels, pool=False):
    layers = [
        nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(inplace=True),
    ]
    if pool:
        layers.append(nn.MaxPool2d(4))
    return nn.Sequential(*layers)


# resnet architecture
class ResNet9(ImageClassificationBase):
    def __init__(self, in_channels, num_diseases):
        super().__init__()

        self.conv1 = ConvBlock(in_channels, 64)
        self.conv2 = ConvBlock(64, 128, pool=True)  # out_dim : 128 x 64 x 64
        self.res1 = nn.Sequential(ConvBlock(128, 128), ConvBlock(128, 128))

        self.conv3 = ConvBlock(128, 256, pool=True)  # out_dim : 256 x 16 x 16
        self.conv4 = ConvBlock(256, 512, pool=True)  # out_dim : 512 x 4 x 44
        self.res2 = nn.Sequential(ConvBlock(512, 512), ConvBlock(512, 512))

        self.classifier = nn.Sequential(
            nn.MaxPool2d(4), nn.Flatten(), nn.Linear(512, num_diseases)
        )

    def forward(self, xb):  # xb is the loaded batch
        out = self.conv1(xb)
        out = self.conv2(out)
        out = self.res1(out) + out
        out = self.conv3(out)
        out = self.conv4(out)
        out = self.res2(out) + out
        out = self.classifier(out)
        return out


model = torch.load(model_path, map_location=("cpu"))


model.eval()


# image_path = r"D:\VS_Code\Assignments\FastAPI\mainProj\app\smaple\smaple1 Apple___Apple_scab.jpeg"
relative_image_path = "../smaple/smaple1 Apple___Apple_scab.jpeg"
image_path = os.path.join(absolute_path, relative_image_path)


def model_prediction_fn():
    image = Image.open(image_path)
    transform = transforms.Compose(
        [
            transforms.Resize((256, 256)),  # Resize the image to (256, 256)
            transforms.ToTensor(),  # Convert the image to a PyTorch tensor
        ]
    )
    image = transform(image)
    image = image.unsqueeze(0)
    with torch.no_grad():
        output = model(image)

    max_index = torch.argmax(output[0], dim=0)
    print(image_labels[max_index])


model_prediction_fn()