import torch
import torch.nn as nn
from torchvision.models import resnet152


class Flatten(nn.Module):
    def __init__(self):
        super(Flatten, self).__init__()

    def forward(self, input):
        return input.view(input.size()[0], -1)


class AuxConv(nn.Module):
    def __init__(self, in_channels, c_tag, stride=1, p=0):
        super(AuxConv, self).__init__()
        self.aux = nn.Sequential(nn.Conv2d(in_channels, c_tag, kernel_size=(3, 1)),
                                 nn.ReLU(),
                                 nn.Dropout(p),
                                 nn.Conv2d(c_tag, c_tag, kernel_size=(1, 3)),
                                 nn.ReLU(),
                                 nn.Dropout(p),
                                 Flatten())

    def forward(self, input):
        return self.aux(input)


class DEN(nn.Module):
    def __init__(self, backbone_wts=None, backbone_freeze=True, p=0):
        super(DEN, self).__init__()

        resnet = resnet152(pretrained=False)
        if backbone_wts != None:
            resnet = self._init_resnet(resnet, backbone_wts)
        
        if backbone_freeze:
            for param in resnet.parameters():
                param.requires_grad = False
            
        
        # prepare the network
        self._flat_resnet152(resnet)

        aux_1024 = [AuxConv(in_channels=1024, c_tag=8, p=p) for _ in range(16)]
        aux_2048 = [AuxConv(in_channels=2048, c_tag=64, p=p) for _ in range(3)]
        self.aux_modules = nn.ModuleList(aux_1024 + aux_2048)
        
        self._init_added_weights()
        
    def _init_resnet(self, resnet, backbone_wts):
        num_ftrs = resnet.fc.in_features
        print("fc", num_ftrs, "x", 128*416)
        resnet.fc = nn.Linear(num_ftrs, 128 * 416)
        resnet.load_state_dict(torch.load(backbone_wts))

        return resnet


    def _init_added_weights(self):
        
        nn.init.xavier_uniform_(self.fc.weight)
        for name,param in self.aux_modules.named_parameters():
            if 'weight' in name:
                nn.init.xavier_uniform_(param)
    
    
    def _flat_resnet152(self, model):
        
        # break the resent to its building blocks
        # into a list
        flattened = []
        flattened += list(model.children())[:4]

        for i in range(4,8):
            sequence = list(model.children())[i]
            flattened += list(sequence.children())

        flattened += list(model.children())[-2:]

        self.resnet_top = nn.Sequential(*flattened[:35])
        # self.resnet_mid = nn.ModuleList(flattened[35:54])
        self.resnet_mid = nn.ModuleList(flattened[35:51])
        self.avg_pool2d = flattened[54]
        self.fc = nn.Linear(25280, 128 * 416)
        # self.fc = nn.Linear(59392, 128*416)
    
    def forward(self, input):
        # print("right after in den", input.shape) 
        x = self.resnet_top(input)
        # print("after resnet_top", x.shape)
        outputs = []
        for i, block in enumerate(self.resnet_mid):
            x = block(x)
            # print("resnet_mid loop", x.shape)
            outputs.append(self.aux_modules[i](x))
            
        x = self.avg_pool2d(x)
        print("after pooling", x.shape)
        x = x.view(x.shape[0], -1)
        outputs.append(x)
        outputs_concat = torch.cat(outputs, dim=1)
        print("output concat", outputs_concat.shape)
        out = self.fc(outputs_concat)
        print("output shape", out.shape)

        return out
